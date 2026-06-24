# Cisco PnP — Génération de snippets de configuration

`scripts/expand_switch_selection.py` génère des snippets de configuration pour les switches Cisco dans le cadre du workflow Plug-and-Play (PnP).

## Utilisation

```bash
.venv/bin/python3 scripts/expand_switch_selection.py --help
```

## Déploiement

Les playbooks PnP se trouvent dans `playbooks/cisco-pnp/`. Pour les exécuter avec l'inventaire approprié :

```bash
make cisco-pnp/deployment inventory_name=event
make cisco-pnp/deployment inventory_name=sc
make cisco-pnp/deployment inventory_name=summercamp
```
