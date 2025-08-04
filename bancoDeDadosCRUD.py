import json
import mysql.connector
from mysql.connector import Error
import logging

'''
CRIAR ARQUIVO config.json COM AS CONFIGURAÇÕES DO BANCO DE DADOS

Exemplo de config.json:
{
  "bd": {
    "HOST": "localhost",
    "PORT": 3306,
    "DATABASE": "sistema",
    "USER": "root",
    "PASSWORD": ""
  }
}
'''

logger = logging.getLogger(__name__)

########################################################
#             Função Salvar dados no Banco
########################################################
def salvar_alterar_ler_dados_tabela(tabela: str, dados: dict, config_path: str = "config.json") -> int | dict | list:
    """
    Insere, atualiza ou lê dados de uma tabela MySQL.

    Parâmetros:
    - tabela: nome da tabela
    - dados: dicionário com:
        * modo: "Salvar" (default) ou "Ler"
        * COLUNAS: lista de colunas a retornar no SELECT
        * LIMIT: int
        * ORDER_BY: str
        * filtros: lista de tuplas (coluna, operador, valor) para SELECT
        * WHERE: dict com cláusula WHERE para UPDATE sem usar ID
        * id: usado para UPDATE simples
    - config_path: arquivo de config JSON com credenciais do banco

    Retorna:
    - int (ID afetado), ou dict/list (dados), ou -1 em caso de erro
    """
    modo = dados.get("modo", "Salvar").lower()

    if not tabela or not isinstance(dados, dict):
        logger.error("❌ Parâmetros inválidos.")
        return -1

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            bd = cfg.get("bd", cfg)
    except Exception as e:
        logger.error(f"❌ Erro ao carregar config: {e}")
        return -1

    try:
        conn = mysql.connector.connect(
            host=bd.get("HOST", "localhost"),
            port=bd.get("PORT", 3306),
            database=bd.get("DATABASE", "sdt"),
            user=bd.get("USER", "root"),
            password=bd.get("PASSWORD", "")
        )
        cursor = conn.cursor(dictionary=True if modo == "ler" else False)

        if modo == "salvar":
            dados = dados.copy()
            where_custom = dados.pop("WHERE", None)
            dados.pop("modo", None)
            is_update = where_custom or ("id" in dados and dados["id"] not in [None, "", 0])

            if is_update:
                # UPDATE
                update_cols = [col for col in dados if col != "id"]
                set_clause = ", ".join([f"{col}=%s" for col in update_cols])
                valores = [dados[col] for col in update_cols]

                if where_custom:
                    where_clause = " AND ".join([f"{col} = %s" for col in where_custom])
                    valores += list(where_custom.values())
                    sql = f"UPDATE {tabela} SET {set_clause} WHERE {where_clause}"
                else:
                    sql = f"UPDATE {tabela} SET {set_clause} WHERE id=%s"
                    valores.append(dados["id"])

                cursor.execute(sql, valores)
                conn.commit()
                logger.info(f"✅ Registro ATUALIZADO na tabela '{tabela}'")
                return dados.get("id", 0)

            else:
                # INSERT
                colunas = ", ".join(dados.keys())
                placeholders = ", ".join(['%s'] * len(dados))
                valores = list(dados.values())
                sql = f"INSERT INTO {tabela} ({colunas}) VALUES ({placeholders})"
                cursor.execute(sql, valores)
                conn.commit()
                last_id = cursor.lastrowid
                logger.info(f"✅ Registro INSERIDO na tabela '{tabela}' com ID: {last_id}")
                return last_id

        elif modo == "ler":
            filtros = dados.copy()
            filtros.pop("modo", None)

            colunas = filtros.pop("COLUNAS", "*")
            colunas_sql = ", ".join(colunas) if isinstance(colunas, list) else "*"

            limit = filtros.pop("LIMIT", None)
            order = filtros.pop("ORDER_BY", None)

            where_clauses = []
            valores = []

            if "filtros" in filtros:
                for col, op, val in filtros.pop("filtros"):
                    where_clauses.append(f"{col} {op} %s")
                    valores.append(val)

            for col, val in filtros.items():
                where_clauses.append(f"{col} = %s")
                valores.append(val)

            where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            sql = f"SELECT {colunas_sql} FROM {tabela}{where_sql}"
            if order:
                sql += f" ORDER BY {order}"
            if limit:
                sql += f" LIMIT {limit}"

            cursor.execute(sql, valores)
            rows = cursor.fetchall()
            logger.info(f"🔎 {len(rows)} registro(s) lido(s) da tabela '{tabela}'")
            return rows[0] if limit == 1 and rows else rows

        else:
            logger.error("❌ Modo inválido. Use 'Salvar' ou 'Ler'.")
            return -1

    except Error as e:
        logger.error(f"❌ Erro de banco: {e}")
        return -1
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()

'''
MODO DE USO:

# Inserir novo registro:
salvar_alterar_ler_dados_tabela("entradas", {
    "telegram_id": 123456,
    "plataforma": "IQOPTION",
    "status": "PENDENTE"
})

# Atualizar registro pelo id:
salvar_alterar_ler_dados_tabela("entradas", {
    "modo": "Salvar",
    "id": 7,
    "status": "FECHADO"
})

# Atualizar com WHERE personalizado:
salvar_alterar_ler_dados_tabela("entradas", {
    "modo": "Salvar",
    "WHERE": {
        "telegram_id": 123456,
        "status": "PENDENTE"
    },
    "plataforma": "IQOPTION"
})

# SELECT simples com filtro padrão:
salvar_alterar_ler_dados_tabela("entradas", {
    "modo": "Ler",
    "status": "PENDENTE",
    "LIMIT": 1
})

# SELECT simples com filtro padrão e colunas específicas:
salvar_alterar_ler_dados_tabela("entradas", {
    "modo": "Ler",
    "status": "PENDENTE",
    "COLUNAS": ["id", "telegram_id", "plataforma"]
})

#SELECT com filtros avançados (operadores)
salvar_alterar_ler_dados_tabela("entradas", {
    "modo": "Ler",
    "filtros": [
        ("status", "=", "PENDENTE"),
        ("datahora", ">", "2025-08-01 00:00:00")
    ],
    "COLUNAS": ["id", "telegram_id", "datahora"],
    "ORDER_BY": "datahora ASC",
    "LIMIT": 1
})
'''
def normalizar_datahora(data_str, hora_str):
    """
    Junta data e hora, garante formato 'YYYY-MM-DD HH:MM:SS'
    """
    datahora_str = f"{data_str.strip()} {hora_str.strip()}"
    # Tenta montar com segundos, senão adiciona ':00'
    try:
        datahora = datetime.strptime(datahora_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # Se estiver faltando segundos, adiciona ':00'
        if len(datahora_str) == 16:  # 'YYYY-MM-DD HH:MM'
            datahora_str += ':00'
        datahora = datetime.strptime(datahora_str, "%Y-%m-%d %H:%M:%S")
    return datahora
#-----------------------------------------------------------------------------------


salvar_alterar_ler_dados_tabela("entradas", {
    "modo": "Ler",
    "status": "PENDENTE",
    "LIMIT": 1
})