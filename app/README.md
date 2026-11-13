```markdown
# Sumário

Autoria:
* Alice de Azevedo Silva (202207340)
* Lara Neiva Carvalho (202407399)
* Ana Sofia Pinto Santos (202407301)

Grupo 51 — Unidade Curricular de Bases de Dados (CC2005), FCUP.

Aplicação Python demonstrando o acesso à BD Disney+ (Catálogo de Filmes e Séries).

# Referência

- [sqlite3](https://docs.python.org/3/library/sqlite3.html)
- [Flask](https://flask.palletsprojects.com/en/2.0.x/)
- [Jinja templates](https://jinja.palletsprojects.com/en/3.0.x/)
- [Pandas](https://pandas.pydata.org/)


# Instalação de dependências

## Python 3 e pip

Deve ter o Python 3 e o gestor de pacotes pip instalado. Pode
instalar os mesmos em Ubuntu por exemplo usando:

```

sudo apt-get install python3 python3-pip

```

## Bibliotecas Python

```

pip3 install --user Flask pandas

```


# Execução

Certifique-se de que o ficheiro `disney.db` está no mesmo diretorio.
Inicie a aplicação executando `python3 server.py` e interaja com a mesma
abrindo uma janela no seu browser com o endereço [__http://localhost:9001/__](http://localhost:9001/)

```

$ python3 server.py
2025-12-10 16:30:00 - INFO - Connected to database disney.db

  * Serving Flask app 'app'
  * Debug mode: on
    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
  * Running on all addresses (0.0.0.0)
  * Running on [http://127.0.0.1:9001](https://www.google.com/search?q=http://127.0.0.1:9001)
  * Running on [http://192.168.1.100:9001](https://www.google.com/search?q=http://192.168.1.100:9001) (Press CTRL+C to quit)
    ...

<!-- end list -->

```

# Notas Adicionais

### Povoamento da Base de Dados
Caso o ficheiro `disney.db` não exista ou precise de ser regenerado, pode criá-lo executando o script de povoamento:

```

python3 criar\_database.py

```

### Inspeção Rápida
Para verificar o conteúdo de uma tabela via terminal (script auxiliar):

```

python3 inspect\_table.py Content

```
```