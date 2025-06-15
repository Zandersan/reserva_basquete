import time
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
import smtplib
from email.message import EmailMessage
import os

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
    with open(ARQ_CPF, 'r') as f:
        cpfs = []
        for linha in f:
            linha = linha.strip()
            if linha:
                # Pega apenas a parte numérica do CPF (antes do |)
                cpf = linha.split('|')[0].strip()
                cpfs.append(cpf)
    
    with open(ARQ_SENHA, 'r') as f:
        senhas = [l.strip() for l in f if l.strip()]
    
    if len(cpfs) != len(senhas):
        raise Exception("Quantidade de CPFs e senhas diferentes.")
    return list(zip(cpfs, senhas))

def ler_agendados():
    agendados = {}
    if os.path.exists(ARQ_AGENDADOS):
        with open(ARQ_AGENDADOS, 'r') as f:
            for linha in f:
                partes = linha.strip().split('|')
                if len(partes) >= 3:
                    cpf = partes[0].strip()
                    data_str = partes[1].strip()
                    # Verifica se a data do agendamento ainda não passou
                    try:
                        data_agendamento = datetime.strptime(data_str, "%Y-%m-%d").date()
                        if data_agendamento >= datetime.now().date():
                            agendados[cpf] = data_agendamento
                    except ValueError:
                        continue
    return agendados

def salvar_agendado(cpf, nome, data, horario):
    with open(ARQ_AGENDADOS, 'a') as f:
        f.write(f"{cpf}|{nome}|{data.isoformat()}|{horario}\n")

def get_nome_por_cpf(cpf):
    with open(ARQ_CPF, 'r') as f:
        for linha in f:
            partes = linha.strip().split('|')
            if len(partes) >= 2 and partes[0].strip() == cpf:
                return partes[1].strip()
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
            partes = linha.strip().split('|')
            if len(partes) >= 3:
                _, _, data_str, horario = partes
                if data_str == data_domingo.isoformat() and horario in ["12:00", "13:00"]:
                    count += 1
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
    nome = get_nome_por_cpf(cpf)
    if not nome:
        nome = "Nome não encontrado"
    
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    try:
        driver.get("https://curitibaemmovimento.curitiba.pr.gov.br/")
        wait.until(EC.element_to_be_clickable((By.ID, "btnPortal"))).click()
        wait.until(EC.element_to_be_clickable((By.ID, "brasileiro"))).click()
        wait.until(EC.presence_of_element_located((By.ID, "documento"))).send_keys(cpf)
        driver.find_element(By.ID, "btnProximo").click()
        wait.until(EC.presence_of_element_located((By.ID, "senha"))).send_keys(senha)
        driver.find_element(By.ID, "btnSenhaProximo").click()

        # Verifica se já está reservado
        try:
            status_element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[@id='cardsReserva']/div[1]/div/div[1]/p[1]/button")))
            if "Reservado" in status_element.text:
                print(f"CPF {cpf} já possui reserva ativa. Pulando...")
                # Pega a data da reserva existente (você pode precisar ajustar isso conforme a página)
                data_reserva = datetime.now().date()  # Substitua por como você obtém a data da reserva existente
                salvar_agendado(cpf, nome, data_reserva, "Horário existente")
                driver.quit()
                return False
        except (TimeoutException, NoSuchElementException):
            pass

        wait.until(EC.element_to_be_clickable((By.ID, "btnNovaReserva"))).click()

        Select(wait.until(EC.presence_of_element_located((By.ID, "selectAtividade")))).select_by_visible_text('Basquetebol')
        Select(driver.find_element(By.ID, "selectNucleo")).select_by_visible_text('Unidade Regional Boa Vista')
        Select(driver.find_element(By.ID, "selectUnidade")).select_by_visible_text('CENTRO DE ESPORTE E LAZER RUA DA CIDADANIA BOA VISTA')
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
        time.sleep(2)

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
                    if texto_hora in ["12:00", "13:00"]:
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
        horario_intervalo = f"{horario_escolhido} às {horario_escolhido[:2]}:59"
        Select(wait.until(EC.presence_of_element_located((By.ID, "selectHorario")))).select_by_visible_text(horario_intervalo)
        wait.until(EC.presence_of_element_located((By.ID, "linkConfirmacao")))
        driver.find_element(By.ID, "linkConfirmacao").click()
        
        checkbox = wait.until(EC.presence_of_element_located((By.ID, "checkResponsabilidade")))
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", checkbox)

        wait.until(EC.element_to_be_clickable((By.ID, "btnContinuar"))).click()

        time.sleep(5)
        salvar_agendado(cpf, nome, data_domingo, horario_escolhido)
        enviar_email_com_confirmacao(cpf, nome, data_domingo, horario_escolhido)
        print(f"Reserva feita para {cpf} ({nome}) em {data_domingo} - {horario_escolhido}")
        driver.quit()
        return True
    except Exception as e:
        print(f"Erro para CPF {cpf}: {e}")
        driver.quit()
        return False

def main():
    agendados = ler_agendados()
    cpfs_senhas = ler_cpfs_senhas()
    hoje = datetime.now().date()

    for cpf, senha in cpfs_senhas:
        # Verifica se já tem agendamento ativo
        if cpf in agendados:
            print(f"CPF {cpf} já possui agendamento ativo para {agendados[cpf]}. Pulando...")
            continue
            
        print(f"Tentando com CPF: {cpf}")
        data_busca = proximo_domingo_apos(hoje - timedelta(days=1))
        tentativas = 0

        while tentativas < 10:
            if data_busca > hoje + timedelta(days=60):
                print(f"Data {data_busca} passou do limite de 2 meses. Reiniciando a busca...")
                data_busca = proximo_domingo_apos(hoje)
                tentativas += 1
                continue

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

if __name__ == "__main__":
    main()