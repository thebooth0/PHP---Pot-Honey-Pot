# SSH Honeypot Dashboard

Ce projet est un **honeypot SSH** qui enregistre les tentatives de connexion SSH et fournit un **dashboard HTML** interactif avec statistiques et géolocalisation des IPs attaquantes.

---

## Prérequis

- **Système :** Linux (Ubuntu, Debian, etc.)
- **Python :** 3.11 recommandé
- **MariaDB / MySQL** pour stocker les logs
- **Python modules :**
  - `pymysql`
  - `paramiko`
- **Accès root** ou sudo pour écouter un port <1024 ou le port choisi

Installation des dépendances Python :

```bash
pip3 install pymysql paramiko
```

Installation de MariaDB sur Debian/Ubuntu :

```bash
sudo apt update
sudo apt install mariadb-server
sudo systemctl enable --now mariadb
```

## Initialisation de la base de données

1. Connectez-vous à MariaDB en tant que root :
```bash
mysql -u root -p
```
2. Créez la base de données et l’utilisateur :
```sql
CREATE DATABASE honeypot;
CREATE USER 'honeypot'@'127.0.0.1' IDENTIFIED BY 'ChangeME';
GRANT ALL PRIVILEGES ON honeypot.* TO 'honeypot'@'127.0.0.1';
FLUSH PRIVILEGES;
```

3. Créez les tables nécessaires :
```sql
USE honeypot;

CREATE TABLE ssh_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DOUBLE NOT NULL,
    ip VARCHAR(45) NOT NULL,
    username VARCHAR(255),
    password VARCHAR(255)
);

CREATE TABLE ip_geolocation (
    ip VARCHAR(45) PRIMARY KEY,
    country VARCHAR(100),
    countryCode VARCHAR(10),
    region VARCHAR(100),
    regionName VARCHAR(100),
    city VARCHAR(100),
    zip VARCHAR(20),
    lat DOUBLE,
    lon DOUBLE,
    timezone VARCHAR(50),
    isp VARCHAR(255),
    org VARCHAR(255),
    count INT DEFAULT 1,
    as VARCHAR(50),
    last_update DOUBLE
);
```

## Configuration
- Vérifiez le fichier honeypot_ssh.py et mettez à jour la configuration DB :
```python
DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "honeypot",
    "password": "VOTRE_MOT_DE_PASSE",
    "database": "honeypot",
    "charset": "utf8mb4",
    "autocommit": True
}
```
## Utilisation

1. Démarrer le honeypot SSH (port par défaut 2022) :
```bash
python3 honeypot_ssh.py
```

2. Générer le dashboard HTML :
```bash
python3 generate_dashboard.py
```
- Pour ma part j'ai ajouter au crontab : `* * * * * bash /path/to/generate_dashboard.py`
- Le fichier index.html sera généré dans le même dossier.
- Ouvrez-le dans votre navigateur pour visualiser les statistiques et la carte des IPs.

## Fonctionnalités
- Collecte des tentatives SSH (username, password, IP, timestamp)
- Géolocalisation des IPs
- Dashboard interactif avec :
  - Graphiques des tentatives par heure et par jour
  - Top 100 des usernames, passwords et combinaisons
  - Top 100 des IPs et leur localisation
  - Carte du monde avec cercles indiquant les attaques par localisation


## Images : 
![](img/img1)
![](img/img2)
