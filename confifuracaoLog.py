# Inicializa colorama
from colorama import init, Fore, Style
init(autoreset=True)

import logging
import os
import json
import mysql.connector
from datetime import datetime

# Cria pasta de logs
diretorio_logs = "logger"
os.makedirs(diretorio_logs, exist_ok=True)

# Nome do arquivo de log com data atual
data_atual = datetime.now().strftime("%Y-%m-%d")
arquivo_log = os.path.join(diretorio_logs, f"log_iqCompluence_{data_atual}.txt")

# ------------------------------------------------------------------------------
# Função existente para salvar no banco
from sua_biblioteca import salvar_alterar_ler_dados_tabela  # ajuste o import

# ------------------------------------------------------------------------------
# Handler personalizado que atualiza status no banco
class StatusDBHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            nivel = record.levelno
            status = None

            if nivel == logging.INFO:
                status = "Online"
            elif nivel == logging.WARNING:
                status = "Offline"
            elif nivel in (logging.ERROR, logging.CRITICAL):
                status = "Error"

            if status:
                salvar_alterar_ler_dados_tabela("status_gerador_sinais", {
                    "modo": "Salvar",
                    "id": 1,
                    "status": status,
                    "obs": msg[:500]  # evita string longa no campo obs
                })

        except Exception as e:
            print(f"Erro ao atualizar status no banco: {e}")

# ------------------------------------------------------------------------------
# Configuração do logger padrão com arquivo + console + banco

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Formato de log
log_format = logging.Formatter(
    fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# FileHandler → grava no arquivo
fh = logging.FileHandler(arquivo_log, encoding="utf-8")
fh.setFormatter(log_format)

# StreamHandler → imprime no terminal
sh = logging.StreamHandler()
sh.setFormatter(log_format)

# StatusDBHandler → atualiza status no banco
db_handler = StatusDBHandler()
db_handler.setFormatter(log_format)

# Adiciona todos os handlers
logger.addHandler(fh)
logger.addHandler(sh)
logger.addHandler(db_handler)



logger.info("🔄 Sistema em execução...")
logger.warning("⚠️ Conexão instável com a IQ Option.")
logger.error(Fore.RED + "❌ Erro ao processar candle.")

