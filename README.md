# Alpha Token Transfer APIs

Alpha Token Transfer APIs

## Install

1. Create Virtual Env: 
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install requirements:
```bash
pip install -r requirement.txt
```

3. Setup Environmet Variables. 

Run following command to copy `.env` file from `.env.template`. 
```bash
cp src/.env.template src/.env
```

3.1. Generate Cipher text for mnemonic: 

```
cd src && python3 cli.py generate-cipher-text
```

You'll be required to put mnemonic text and password. This password will be used to run the app. 

Copy output text and paste into `src/.env` file. 

3.2. Generate JWT Secret key:

Run following command to generate JWT Secret key:
```bash
python3 cli.py generate-jwt-secret
```

Copy output into `src/.env` file. 

You need to fill `HOTKEY` and `NET_UID` properly in `.env` file. 

4. Run application. 

```bash
python3 app.py
```

## Test API 

You can test transfer using CLI: 
```bash
python3 cli.py transfer-balance --coldkeys=5CqvqYU8DSCQRd8j8GxGpWrYFWihraXvxjXjsAaU2AF9hs59,5HQtHtkorV8yrPzvUgPomHvcZuFoscvD1Js7vTaJanB4ZKme --amount_in_usd=10
```