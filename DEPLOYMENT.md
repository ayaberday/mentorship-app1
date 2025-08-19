# Guide de déploiement sur Render

Ce guide vous explique comment déployer l'application Mentorship sur Render.

## Prérequis

1. Compte GitHub avec le code de l'application
2. Compte Render (gratuit)
3. Configuration email (Gmail recommandé)

## Étapes de déploiement

### 1. Préparation du repository GitHub

1. Assurez-vous que tous les fichiers sont dans votre repository :
   - `render.yaml`
   - `requirements.txt`
   - `build.sh`
   - `runtime.txt`
   - `.gitignore`
   - Code de l'application

2. Commitez et poussez tous les changements :
   \`\`\`bash
   git add .
   git commit -m "Préparation pour déploiement Render"
   git push origin main
   \`\`\`

### 2. Configuration sur Render

1. Connectez-vous à [Render](https://render.com)
2. Cliquez sur "New +" → "Blueprint"
3. Connectez votre repository GitHub
4. Sélectionnez le repository de l'application
5. Render détectera automatiquement le fichier `render.yaml`

### 3. Configuration des variables d'environnement

Les variables suivantes seront configurées automatiquement via `render.yaml` :

**Variables automatiques :**
- `DATABASE_URL` (générée par Render)
- `SECRET_KEY` (générée automatiquement)
- `DEBUG=False`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`

**Variables à configurer manuellement :**

1. Dans le dashboard Render, allez dans votre service web
2. Cliquez sur "Environment"
3. Ajoutez ces variables :

\`\`\`
EMAIL_HOST_USER=votre-email@gmail.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe-app
\`\`\`

### 4. Configuration Gmail

1. Activez l'authentification à 2 facteurs sur votre compte Gmail
2. Générez un mot de passe d'application :
   - Allez dans les paramètres Google
   - Sécurité → Authentification à 2 facteurs → Mots de passe des applications
   - Générez un mot de passe pour "Django App"
3. Utilisez ce mot de passe dans `EMAIL_HOST_PASSWORD`

### 5. Déploiement

1. Cliquez sur "Create Blueprint"
2. Render va :
   - Créer la base de données PostgreSQL
   - Déployer l'application web
   - Exécuter les migrations
   - Créer le superutilisateur (admin/admin123)

### 6. Vérification

1. Une fois le déploiement terminé, visitez l'URL fournie
2. Testez la connexion avec le compte admin
3. Vérifiez que les emails fonctionnent

## Configuration post-déploiement

### Création des comptes utilisateurs

1. Connectez-vous avec le compte admin
2. Créez les comptes RH nécessaires
3. Les RH pourront ensuite créer les programmes et binômes

### Configuration des notifications

Les notifications sont activées par défaut. Pour les modifier :

1. Dans Render, allez dans Environment
2. Modifiez les variables `NOTIFICATION_SETTINGS_*`

### Sauvegarde de la base de données

Render sauvegarde automatiquement votre base de données PostgreSQL.

## Maintenance

### Mise à jour de l'application

1. Poussez vos changements sur GitHub
2. Render redéploiera automatiquement

### Monitoring

1. Consultez les logs dans le dashboard Render
2. Surveillez les métriques de performance
3. Configurez des alertes si nécessaire

### Commandes utiles

Pour exécuter des commandes Django sur Render :

\`\`\`bash
# Se connecter au shell
python manage.py shell

# Créer un superutilisateur
python manage.py createsuperuser

# Voir les migrations
python manage.py showmigrations

# Collecter les fichiers statiques
python manage.py collectstatic
\`\`\`

## Dépannage

### Problèmes courants

1. **Erreur 500** : Vérifiez les logs dans Render
2. **Emails non envoyés** : Vérifiez la configuration Gmail
3. **Fichiers statiques manquants** : Vérifiez `STATIC_ROOT` et `collectstatic`
4. **Base de données** : Vérifiez `DATABASE_URL`

### Support

- Documentation Render : https://render.com/docs
- Logs de l'application : Dashboard Render → Logs
- Issues GitHub : Créez une issue dans le repository

## Sécurité

### Recommandations

1. Changez le mot de passe admin par défaut
2. Utilisez des mots de passe forts pour tous les comptes
3. Surveillez les logs d'accès
4. Mettez à jour régulièrement les dépendances

### Variables sensibles

Ne jamais commiter :
- Mots de passe
- Clés API
- Tokens d'authentification
- Variables d'environnement de production

## Performance

### Optimisations

1. Utilisez le plan payant pour de meilleures performances
2. Configurez un CDN pour les fichiers statiques
3. Optimisez les requêtes de base de données
4. Surveillez l'utilisation mémoire

### Monitoring

1. Activez les métriques Render
2. Configurez des alertes
3. Surveillez les temps de réponse
4. Analysez les logs d'erreur
