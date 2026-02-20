import time
import traceback
from datetime import datetime, timedelta
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import smtplib
from email.message import EmailMessage
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from cryptography.fernet import Fernet
import base64

# Configurações de criptografia
def carregar_chave():
    chave_file = 'chave_criptografia.key'
    if os.path.exists(chave_file):
        with open(chave_file, 'rb') as f:
            return f.read()
    else:
        chave = Fernet.generate_key()
        with open(chave_file, 'wb') as f:
            f.write(chave)
        return chave

CHAVE_CRIPTOGRAFIA = carregar_chave()
cipher_suite = Fernet(CHAVE_CRIPTOGRAFIA)

# Funções para criptografar e descriptografar
def criptografar(texto):
    return cipher_suite.encrypt(texto.encode()).decode()

def descriptografar(texto_criptografado):
    return cipher_suite.decrypt(texto_criptografado.encode()).decode()

# Função para migrar dados não criptografados para criptografados
def migrar_dados_criptografados():
    # Migrar CPFs
    if os.path.exists(ARQ_CPF):
        with open(ARQ_CPF, 'r') as f:
            linhas = f.readlines()
        
        # Verificar se já está criptografado (olhando a primeira linha)
        if linhas and not linhas[0].startswith('gAAAAA'):
            print("Migrando CPFs para formato criptografado...")
            with open(ARQ_CPF, 'w') as f:
                for linha in linhas:
                    linha = linha.strip()
                    if linha:
                        linha_criptografada = criptografar(linha)
                        f.write(linha_criptografada + '\n')
    
    # Migrar senhas
    if os.path.exists(ARQ_SENHA):
        with open(ARQ_SENHA, 'r') as f:
            linhas = f.readlines()
        
        if linhas and not linhas[0].startswith('gAAAAA'):
            print("Migrando senhas para formato criptografado...")
            with open(ARQ_SENHA, 'w') as f:
                for linha in linhas:
                    linha = linha.strip()
                    if linha:
                        linha_criptografada = criptografar(linha)
                        f.write(linha_criptografada + '\n')
    
    # Migrar agendados
    if os.path.exists(ARQ_AGENDADOS):
        with open(ARQ_AGENDADOS, 'r') as f:
            linhas = f.readlines()
        
        if linhas and not linhas[0].startswith('gAAAAA'):
            print("Migrando agendados para formato criptografado...")
            with open(ARQ_AGENDADOS, 'w') as f:
                for linha in linhas:
                    linha = linha.strip()
                    if linha:
                        linha_criptografada = criptografar(linha)
                        f.write(linha_criptografada + '\n')

# Config SMTP
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'alezandersansan@gmail.com'
SMTP_PASS = 'uuqn przv bdef zkqm'
EMAIL_DESTINO = 'alerorocha@hotmail.com'

ARQ_CPF = 'cpf.txt'
ARQ_SENHA = 'senha.txt'
ARQ_AGENDADOS = 'agendados.txt'

WAIT_TIMEOUT = 15

def ler_cpfs_senhas():
    cpfs = []
    senhas = []
    
    # Migrar dados primeiro
    migrar_dados_criptografados()
    
    # Ler CPFs criptografados
    if os.path.exists(ARQ_CPF):
        with open(ARQ_CPF, 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        # Descriptografa a linha
                        linha_descriptografada = descriptografar(linha)
                        # Pega apenas a parte numérica do CPF (antes do |)
                        cpf = linha_descriptografada.split('|')[0].strip()
                        cpfs.append(cpf)
                    except:
                        print("Erro ao descriptografar linha de CPF")
                        continue
    
    # Ler senhas criptografadas
    if os.path.exists(ARQ_SENHA):
        with open(ARQ_SENHA, 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        senha = descriptografar(linha)
                        senhas.append(senha)
                    except:
                        print("Erro ao descriptografar senha")
                        continue
    
    if len(cpfs) != len(senhas):
        raise Exception("Quantidade de CPFs e senhas diferentes.")
    return list(zip(cpfs, senhas))

# Função para mascarar CPF no output
def mascarar_cpf(cpf):
    if len(cpf) == 11:
        return f"{cpf[:3]}.***.***-{cpf[-2:]}"
    return "***.***.***-**"

def ler_agendados():
    agendados = {}
    if os.path.exists(ARQ_AGENDADOS):
        with open(ARQ_AGENDADOS, 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        linha_descriptografada = descriptografar(linha)
                        partes = linha_descriptografada.split('|')
                        if len(partes) >= 3:
                            cpf = partes[0].strip()
                            data_str = partes[2].strip()
                            # Verifica se a data do agendamento ainda não passou
                            try:
                                data_agendamento = datetime.strptime(data_str, "%Y-%m-%d").date()
                                if data_agendamento >= datetime.now().date():
                                    agendados[cpf] = data_agendamento
                            except ValueError:
                                continue
                    except:
                        print(f"Erro ao descriptografar agendamento: {linha}")
                        continue
    return agendados

def salvar_agendado(cpf, nome, data, horario):
    linha = f"{cpf}|{nome}|{data.isoformat()}|{horario}"
    linha_criptografada = criptografar(linha)
    with open(ARQ_AGENDADOS, 'a') as f:
        f.write(linha_criptografada + '\n')

def get_nome_por_cpf(cpf):
    if os.path.exists(ARQ_CPF):
        with open(ARQ_CPF, 'r') as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    try:
                        linha_descriptografada = descriptografar(linha)
                        partes = linha_descriptografada.split('|')
                        if len(partes) >= 2 and partes[0].strip() == cpf:
                            return partes[1].strip()
                    except:
                        continue
    return ""

def proximo_domingo_apos(data):
    if not isinstance(data, datetime):
        data = datetime.combine(data, datetime.min.time())
    dias_ate_domingo = (6 - data.weekday()) % 7
    if dias_ate_domingo == 0:
        dias_ate_domingo = 7
    return (data + timedelta(days=dias_ate_domingo)).date()

def domingo_cheio(data_domingo):
    if not os.path.exists(ARQ_AGENDADOS):
        return False
    count = 0
    with open(ARQ_AGENDADOS, 'r') as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                try:
                    linha_descriptografada = descriptografar(linha)
                    partes = linha_descriptografada.split('|')
                    if len(partes) >= 3:
                        _, _, data_str, horario = partes
                        if data_str == data_domingo.isoformat() and horario in ["08:00", "09:00"]:
                            count += 1
                except:
                    continue
    return count >= 2

def enviar_email_com_confirmacao(cpf, nome, data, horario):
    msg = EmailMessage()
    msg['Subject'] = f'Confirmação de Reserva - {nome}'
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL_DESTINO
    msg.set_content(f"""
    Confirmação de Reserva:
    
    CPF: {cpf}
    Nome: {nome}
    Data: {data.strftime('%d/%m/%Y')}
    Horário: {horario}
    """)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)
    print('Email enviado com sucesso.')

def tentar_reserva(cpf, senha, data_domingo):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    driver = webdriver.Chrome(options=chrome_options)
    
    nome = get_nome_por_cpf(cpf)
    if not nome:
        nome = "Nome não encontrado"
        
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    try:
        # Verificar se é a data que queremos ignorar
        data_especifica = datetime(2025, 7, 27).date()
        if data_domingo == data_especifica:
            print(f"Data {data_domingo} ignorada para reservas. Pulando CPF: {mascarar_cpf(cpf)}")  # CPF mascarado
            driver.quit()
            return False
            
        driver.get("https://curitibaemmovimento.curitiba.pr.gov.br/")
        print("Página inicial carregada.")
        # Fecha popup inicial se aparecer
        try:
            botao_popup = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//*[@id='btn-fechar-popup']"))
            )
            driver.execute_script("arguments[0].click();", botao_popup)
            print("Popup inicial fechado.")
        except TimeoutException:
            print("Popup não apareceu, seguindo fluxo normal.")
    
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "btnPortal"))).click()
        except TimeoutException:
            print("Timeout: btnPortal não encontrado") 
            print("Título:", driver.title)
            print("URL:", driver.current_url)
            driver.save_screenshot("debug.png")
            with open("pagina_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            raise
        wait.until(EC.element_to_be_clickable((By.ID, "brasileiro"))).click()
        wait.until(EC.presence_of_element_located((By.ID, "documento"))).send_keys(cpf)
        
        try:
            driver.find_element(By.ID, "btnProximo").click()
        except TimeoutException:
            print("Timeout: btnProximo não encontrado")
            print("Título:", driver.title)
            print("URL:", driver.current_url)
            driver.save_screenshot("debug.png")
            with open("pagina_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            raise

        wait.until(EC.presence_of_element_located((By.ID, "senha"))).send_keys(senha)
        try:
            driver.find_element(By.ID, "btnSenhaProximo").click()
        except TimeoutException:
            print("Timeout: btnSenhaProximo não encontrado")
            print("Título:", driver.title)
            print("URL:", driver.current_url)
            driver.save_screenshot("debug.png")
            with open("pagina_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            raise

        try:
            wait.until(EC.element_to_be_clickable((By.ID, "btnNovaReserva"))).click()
        except TimeoutException:
            print("Timeout: btnNovaReserva não encontrado")
            print("Título:", driver.title)
            print("URL:", driver.current_url)
            driver.save_screenshot("debug.png")
            with open("pagina_debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            raise

        Select(wait.until(EC.presence_of_element_located((By.ID, "selectAtividade")))).select_by_visible_text('Basquetebol')
        Select(driver.find_element(By.ID, "selectNucleo")).select_by_visible_text('Unidade Regional Boa Vista')
        Select(driver.find_element(By.ID, "selectUnidade")).select_by_visible_text('CENTRO DE ESPORTE E LAZER AVELINO VIEIRA')
        Select(driver.find_element(By.ID, "selectSugestao")).select_by_visible_text('Não')

        capacidade_input = wait.until(EC.presence_of_element_located((By.ID, "capacidadePessoas")))
        capacidade_input.clear()
        capacidade_input.send_keys("20")
        capacidade_input.send_keys(Keys.TAB)
        time.sleep(1)
        driver.find_element(By.ID, "btnConfirmaCapacidade").click()

        data_input = wait.until(EC.presence_of_element_located((By.ID, "dataReferencia")))
        data_formatada = data_domingo.strftime('%Y-%m-%d')
        driver.execute_script(f"""
            var input = document.getElementById('dataReferencia');
            input.value = '{data_formatada}';
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        """)
        time.sleep(1)
        driver.find_element(By.ID, "btnConfirmaData").click()
        time.sleep(5)

        try:
            msg_erro = driver.find_element(By.XPATH, "//*[contains(text(),'Infelizmente não encontramos nenhum espaço físico')]")
            if msg_erro.is_displayed():
                print("Mensagem de indisponibilidade detectada.")
                driver.quit()
                return False
        except NoSuchElementException:
            pass

        data_formatada_html = datetime.strptime(data_formatada, "%Y-%m-%d").strftime("%d/%m/%Y")

        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'resultado')]")))
        blocos = driver.find_elements(By.XPATH, "//div[contains(@class, 'resultado')]")

        if not blocos:
            print(f"Nenhuma data ou horário disponível para {data_formatada_html}.")
            driver.quit()
            return False

        horario_escolhido = None
        clicou = False

        for bloco in blocos:
            try:
                data_bloco = bloco.find_element(By.XPATH, ".//span[@data-dataagenda]").text.strip()
                if data_bloco != data_formatada_html:
                    continue

                horarios = bloco.find_elements(By.XPATH, ".//span[@data-horarioagenda and not(contains(@class, 'd-none'))]")

                for h in horarios:
                    texto_hora = h.text.strip()
                    if texto_hora in ["08:00", "09:00"]:
                        botao = bloco.find_element(By.XPATH, ".//a[contains(text(), 'Mais detalhes')]")
                        driver.execute_script("arguments[0].click();", botao)
                        horario_escolhido = texto_hora
                        clicou = True
                        break 

                if clicou:
                    break

            except Exception as e:
                print(f"Erro ao processar bloco: {e}")
                continue

        if not clicou:
            print(f"Nenhum horário desejado encontrado para a data {data_formatada_html}.")
            driver.quit()
            return False
        
        wait.until(EC.presence_of_element_located((By.ID, "selectHorario")))
        select_elem = Select(wait.until(EC.presence_of_element_located((By.ID, "selectHorario"))))

        # lista todas as opções disponíveis no select
        opcoes = [opt.text.strip() for opt in select_elem.options]
        print("Opções disponíveis:", opcoes)

        horario_intervalo = None
        if "08:00 às 08:59" in opcoes:
            horario_intervalo = "08:00 às 08:59"
        elif "09:00 às 09:59" in opcoes:
            horario_intervalo = "09:00 às 09:59"

        if horario_intervalo:
            select_elem.select_by_visible_text(horario_intervalo)
            wait.until(EC.presence_of_element_located((By.ID, "linkConfirmacao")))
            driver.find_element(By.ID, "linkConfirmacao").click()
        else:
            print("Nenhum horário das 08h ou 09h disponível.")
            driver.quit()
            return False
        
        checkbox = wait.until(EC.presence_of_element_located((By.ID, "checkResponsabilidade")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", checkbox)

        wait.until(EC.element_to_be_clickable((By.ID, "btnContinuar"))).click()

        time.sleep(5)
        salvar_agendado(cpf, nome, data_domingo, horario_escolhido)
        enviar_email_com_confirmacao(cpf, nome, data_domingo, horario_escolhido)
        print(f"Reserva feita para {mascarar_cpf(cpf)} ({nome}) em {data_domingo} - {horario_escolhido}")  # CPF mascarado
        driver.quit()
        return True
    except Exception as e:
        print(f"Erro para CPF {mascarar_cpf(cpf)}: {e}")  # CPF mascarado
        traceback.print_exc()
        driver.quit()
        return False

def executar_rotina():
    print(f"\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Iniciando nova execução...")
    agendados = ler_agendados()
    cpfs_senhas = ler_cpfs_senhas()
    hoje = datetime.now().date()
    
    limite_atingido_global = False

    for cpf, senha in cpfs_senhas:
        # Verifica se já tem agendamento ativo
        if cpf in agendados:
            data_agendamento = agendados[cpf]
            if data_agendamento >= hoje:
                print(f"CPF {mascarar_cpf(cpf)} já possui agendamento ativo para {data_agendamento}. Pulando...")
                continue
                
        print(f"Tentando com CPF: {mascarar_cpf(cpf)}")  # CPF mascarado no output
        data_busca = proximo_domingo_apos(hoje - timedelta(days=1))
        tentativas = 0
        limite_atingido = False

        while tentativas < 10 and not limite_atingido_global:
            if data_busca > hoje + timedelta(days=30):
                print(f"Data {data_busca} passou do limite de 15 dias. Reiniciando a busca...")
                # Marca que atingiu o limite e sai do loop
                limite_atingido = True
                limite_atingido_global = True
                break

            if domingo_cheio(data_busca):
                print(f"{data_busca} já possui 2 horários agendados. Pulando...")
                data_busca += timedelta(days=7)
                tentativas += 1
                continue

            sucesso = tentar_reserva(cpf, senha, data_busca)
            if sucesso:
                break

            data_busca += timedelta(days=7)
            tentativas += 1
        
        # MODIFICAÇÃO: Se atingiu o limite de datas global, reinicia a busca em vez de parar
        if limite_atingido_global:
            print("Limite de 15 dias atingido. Reiniciando a busca a partir do próximo domingo.")
            # Aguarda um tempo antes de reiniciar
            #time.sleep(300)  # 5 minutos
            break  # Sai do loop de CPFs para reiniciar a execução

def main():
    # Migrar dados na primeira execução
    migrar_dados_criptografados()
    
    while True:
        try:
            executar_rotina()
        except Exception as e:
            print(f"Erro durante a execução: {e}")
            traceback.print_exc()
        
        # Espera 10 minutos antes da próxima execução
        # print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Aguardando 10 minutos para próxima execução...")
        # time.sleep(600)

if __name__ == "__main__":
    main()
