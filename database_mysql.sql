-- Banco opcional para MySQL.
-- O SQLAlchemy cria as tabelas automaticamente ao iniciar o app.
CREATE DATABASE IF NOT EXISTS kipao
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Depois configure:
-- mysql+pymysql://root:SUA_SENHA@localhost/kipao
