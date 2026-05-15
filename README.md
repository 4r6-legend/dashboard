# AWS Billing Dashboard

Streamlit + AWS Cost Explorer (`ce`). Acesso ao dashboard exige **login** (bcrypt via Secrets), no estilo da tela de login do projeto interno *engenharia-assistant*.

## Secrets (Streamlit Cloud ou `.streamlit/secrets.toml`)

1. **AWS** (Cost Explorer):

```toml
[aws]
aws_access_key_id = "..."
aws_secret_access_key = "..."
aws_region = "us-east-1"
```

2. **Usuários do app** (senhas **nunca** em texto puro — use hash bcrypt):

```toml
[credentials.users]
"seu-email@cognitivo.ai" = "$2b$12$...hash_gerado_com_bcrypt..."
```

Gerar hash localmente:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'SUA_SENHA', bcrypt.gensalt()).decode())"
```

Cole o resultado no TOML entre aspas. Sem `[credentials.users]`, ninguém consegue autenticar.

3. **Nome da organização** (obrigatório — títulos e textos do app):

```toml
[gobrax]
display_name = "Nome da sua empresa ou conta"
```

Sem `display_name` preenchido, o app mostra erro e não inicia.

## Rodar

Recomendado (login primeiro):

```bash
pip install -r requirements.txt
streamlit run Login.py
```

Também é possível `streamlit run app.py` (redireciona para `Login.py`).

A IAM user/role precisa de permissão para `ce:GetCostAndUsage` na conta AWS usada pelo Cost Explorer.
