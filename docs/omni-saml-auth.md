# Omni — Authentification SAML et accès de secours

## Architecture

```
Utilisateur → Omni UI → Authentik (SAML) → rôle assigné via SAMLLabelRules
omnictl     → Omni API → service account (clé PGP, sans SAML)
```

L'authentification web passe entièrement par Authentik. Le service account `omni-ansible`
est le seul moyen d'accéder à Omni sans SAML.

## Dépendance circulaire et recovery

Authentik tourne sur le cluster k8s géré par Omni. Si Authentik est down :

- L'UI Omni est inaccessible (SAML broken)
- **Le service account reste fonctionnel** (auth par clé PGP, indépendant de SAML)

Procédure de recovery :

```bash
# 1. Configurer la clé de service account
export OMNI_ENDPOINT=https://omni.etsmtl.club:443/
export OMNI_SERVICE_ACCOUNT_KEY=<clé dans le gestionnaire de mots de passe>

# 2. Récupérer le kubeconfig du cluster
omnictl cluster kubeconfig <nom-du-cluster> --force

# 3. Redémarrer Authentik via kubectl
kubectl -n authentik rollout restart deployment/authentik-server
kubectl -n authentik rollout restart deployment/authentik-worker
```

Une fois Authentik up, l'UI Omni redevient accessible.

## Scénario catastrophe (Omni etcd perdu + Authentik down)

1. Reconstruire Omni : `make omni/deploy` — le flag `--initial-users=admin@etsmtl.club`
   recrée l'utilisateur admin au premier démarrage
2. Redémarrer Authentik directement sur le nœud k8s (kubectl ou accès VM)
3. Se reconnecter à Omni UI via SAML → rôle Admin assigné automatiquement

## Service account

Le service account `omni-ansible` est utilisé par Ansible pour appliquer les SAMLLabelRules
après chaque déploiement. Sa clé est aussi le breaking glass pour l'accès CLI.

**La clé est stockée à deux endroits :**
- Ansible vault : `inventories/infra/host_vars/omni01.prod.etsmtl.club.yaml` (`omni_service_account_key`)
- Gestionnaire de mots de passe du club (Bitwarden) : entrée `Omni — service account omni-ansible`

Pour afficher la clé depuis le vault :

```bash
ansible -i inventories/infra/hosts.ini omni01.prod.etsmtl.club \
  -m debug -a "var=omni_service_account_key" \
  --ask-vault-pass
```

## Attribution des rôles SAML

Les rôles Omni sont assignés automatiquement selon les groupes Authentik de l'utilisateur.
Authentik envoie uniquement les groupes dont le nom commence par `omni-`.

| Groupe Authentik | Rôle Omni |
|-----------------|-----------|
| `omni-admin`    | Admin     |
| `omni-user`     | Operator  |
| `omni-viewer`   | Reader    |

Les règles sont configurées dans `inventories/infra/host_vars/omni01.prod.etsmtl.club.yaml`
(`omni_saml_label_rules`) et appliquées à chaque run Ansible via `omnictl apply`.

`updateoneachlogin: true` — les groupes Authentik sont la source de vérité pour les rôles.
Retirer quelqu'un d'un groupe Authentik révoque son accès à la prochaine connexion.

## Accès initial / utilisateur admin garanti

Le flag `--initial-users=admin@etsmtl.club` dans le docker-compose garantit que cet
utilisateur reçoit le rôle Admin au premier démarrage d'Omni (ou après un reset etcd),
indépendamment des SAMLLabelRules. Il authentifie quand même via SAML.
