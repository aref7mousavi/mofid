## poetry Installation
```bash
curl -sSL https://install.python-poetry.org | python3 -

nano ~/.bash_aliases

    export PATH="$HOME/.local/bin:$PATH"
    export PATH="$HOME/.poetry/bin:$PATH"
```

## poetry commands
```bash
# add package to dev environment
poetry add -C ./configs/pyproject.toml --group dev PACKAGE_NAME

# install only dev
poetry install -C ./configs/pyproject.toml --only dev

# install all dependencies (prod + dev)
poetry install -C ./configs/pyproject.toml
```


## pre-commit commands
```bash
pre-commit install -c configs/.pre-commit-config.yaml

pre-commit run -a -c configs/.pre-commit-config.yaml
```

## Bump version

```bash
python3 scripts/bump.py
```

```env
DEBUG=True
SECRET_KEY=xxxx

CORS_ALLOWED_ORIGINS=http://127.0.0.1:3000,http://127.0.0.1:3100
```
