# WLC Cisco AIR-CT5760 (5570) — Notes de troubleshooting et pitfalls

> Document de référence pour LAN ETS / SummerCamp CTF — basé sur le troubleshooting du
> WLC `wlc` (provision `air-ct5760-6`) et d'un AP Aironet 3700 (AP3G2, image AireOS
> `ap3g2-k9w8-mx.153-3.JN8`) en juin 2026.
>
> Objectif : éviter de re-découvrir les mêmes problèmes dans 1, 2, 5 ans.

---

## ⚠️ Pitfall #1 — Certificat MIC du WLC expiré (LE GROS PROBLÈME)

**Symptôme** : les AP obtiennent une IP DHCP correctement (option 43 fonctionne, le
controller est bien découvert), mais le join CAPWAP échoue en boucle avec :

```
%DTLS-3-HANDSHAKE_FAILURE: ... DTLS handshake timeout-disconnecting...
%DTLS-6-RECORD_IGNORED: Record ignored - expired sequence number.
```

et l'AP reboot complètement entre chaque tentative (nouvelle IP DHCP à chaque cycle :
`.14` → `.15` → `.16`...).

**Cause racine** (visible uniquement côté **console de l'AP**, pas côté WLC) :

```
%PKI-3-CERTIFICATE_INVALID_EXPIRED: Certificate chain validation has failed.
The certificate (SN: 1DF9761C0000001C9621) has expired.
Validity period ended on 11:53:58 UTC Jun 1 2025
```

Le **certificat MIC (Manufacturer Installed Certificate)** du WLC, utilisé pour le
DTLS CAPWAP, a une date d'expiration codée en dur (`Jun 1 2025` pour ce WLC). Une fois
cette date dépassée, **aucun AP avec une horloge correcte ne pourra joindre ce WLC** —
peu importe la config réseau, VLAN, DHCP, etc. C'est un problème connu sur le matériel
Cisco de cette génération (5760 / AIR-CT5760, AP3G2 et similaires).

⚠️ Ne PAS confondre avec le certificat `TP-self-signed-XXXXXXXXXX` (HTTPS GUI,
`crypto pki trustpoint`). Ce n'est PAS le même certificat et le régénérer ne change
rien au problème CAPWAP. (On l'a fait par erreur — ça a juste cassé temporairement le
GUI HTTPS, sans effet sur le DTLS CAPWAP.)

### Solution / workaround appliqué

Reculer l'horloge du **WLC** (et potentiellement de chaque AP) à une date **avant**
l'expiration du certificat — on a utilisé **2018** comme marge confortable.

```
! Sur le WLC
no ntp peer 206.108.0.131
clock set 12:00:00 1 jan 2018
copy run start
```

Une fois le WLC en 2018, l'AP (qui synchronise son horloge via CAPWAP au moment du
handshake) valide le certificat comme "pas encore expiré" et le join réussit.

### ⚠️ Pièges de ce workaround à ne PAS oublier

1. **Pas de RTC fiable sur ce WLC** — au boot, l'horloge revient à `Jan 1 2010` (ou
   `Mar 1 00:00` style epoch sur les AP). **Après CHAQUE reboot du WLC**, il faut
   refaire le `clock set 2018` **avant** que les AP ne tentent leur join, sinon
   retour à la case départ (boucle DTLS).
2. **NTP doit rester désactivé** (`no ntp peer ...`) — sinon le WLC va se
   resynchroniser vers la date réelle (2026+) et recasser le certificat.
   Vérifier après chaque `copy run start` / reload que `no ntp peer` est bien
   persisté.
3. Envisager un script de démarrage / une procédure documentée pour le jour J :
   **dès que le WLC est up, faire le `clock set` avant de brancher les AP**.
4. Si de **nouveaux AP** (jamais joints) sont ajoutés en cours d'événement, vérifier
   qu'ils récupèrent bien l'heure via CAPWAP — sinon `clock set` manuel sur l'AP via
   console aussi (`clock set 12:00:00 1 jan 2018`).

### Piste à explorer pour une solution durable (pas faite, à creuser plus tard)

- Chercher un firmware/patch Cisco qui régénère le certificat MIC avec une nouvelle
  date d'expiration (bug connu, possiblement référencé sous un CSCxx quelconque).
- Vérifier si une mise à jour de l'image AireOS de l'AP et/ou de l'IOS-XE du WLC
  adresse ce problème de validité de certificat.

---

## Pitfall #2 — `ip dhcp snooping` sur le VLAN où le WLC est LUI-MÊME le serveur DHCP

**Symptôme** : le serveur DHCP du WLC reçoit le DISCOVER, log
`Sending DHCPOFFER to client ...` et `broadcasting BOOTREPLY to client ...`, MAIS le
binding reste en état `Selecting` indéfiniment. `show ip dhcp snooping binding` reste
vide. Le ping broadcast (`ping 10.x.255.255`) fonctionne, donc le L2/trunk est OK.

**Cause** : le DHCP snooping actif sur le VLAN local où le WLC fait tourner son propre
pool DHCP (`ip dhcp pool ...`) interfère avec le bridging du BOOTREPLY broadcast généré
par le process DHCP server local — celui-ci semble être traité différemment du trafic
normal d'un port physique trusted.

### Solution appliquée

```
no ip dhcp snooping vlan 67
```

(en gardant le snooping actif sur les autres VLANs, ex. 66, où le serveur DHCP est
externe — Kea — et où le snooping fonctionne normalement)

### À retenir

> **Si le WLC (ou tout switch L3 Cisco) fait office de serveur DHCP local pour un
> VLAN, désactiver `ip dhcp snooping` sur CE VLAN spécifiquement.** Garder le snooping
> uniquement sur les VLANs où le serveur DHCP est externe.

---

## Pitfall #3 — Confusion WLAN ID vs VLAN ID dans `ap group`

Dans la configuration originale (LAN ETS 2025), on avait :

```
wlan TisTheLan 1 Lan_ETS
 client vlan 2354
...
ap group LanETS
 wlan 2354        <-- BUG: référence le VLAN client, pas le WLAN ID !
```

`ap group ... wlan <X>` attend le **WLAN ID** (ici `1`, le `1` dans
`wlan TisTheLan 1 Lan_ETS`), **pas** le VLAN client. Si ces deux nombres sont
différents (ce qui est presque toujours le cas), le SSID ne sera broadcasté par aucun
AP du groupe — sans message d'erreur explicite.

### À retenir

```
wlan <profile-name> <WLAN-ID> <SSID>
 client vlan <VLAN-ID-CLIENT>
...
ap group <nom>
 wlan <WLAN-ID>     <-- bien le WLAN-ID, PAS le VLAN client
```

---

## Pitfall #4 — Ports SFP/SFP+ et PoE

Les ports `TenGigabitEthernet` (SFP/SFP+) du WLC **n'ont pas de PoE**, même avec un
module SFP-to-RJ45 1Gb. Le PoE est injecté par le circuit du port lui-même
(802.3af/at), pas par le module SFP.

Pour brancher un AP nécessitant du PoE sur un de ces ports :

- Injecteur PoE externe entre le SFP-RJ45 et l'AP, ou
- Switch PoE intermédiaire (uplink trunké vers le port SFP du WLC), ou
- Alimentation DC séparée si l'AP a un jack DC dédié.

---

## Pitfall #5 — Spanning-Tree / portfast sur ports access destinés aux AP/devices

Lors d'un test sur `Te1/0/3` (port SFP-RJ45 mis en access VLAN 67 pour
troubleshooting), même avec un lien `connected` à 1Gb, **aucune MAC n'était apprise**
et le DHCP restait bloqué en `Selecting` — pattern similaire au pitfall #2, mais à
l'origine on suspectait STP.

### À retenir

Toujours appliquer sur les ports access destinés à des end-devices (AP, laptop de
troubleshoot, etc.) :

```
interface <port>
 switchport mode access
 switchport access vlan <X>
 spanning-tree portfast
 ip dhcp snooping trust   ! si le serveur DHCP est de l'autre côté du port (uplink)
                            ! — PAS sur un port où un AP/client se connecte directement !
```

⚠️ Attention : `ip dhcp snooping trust` doit être sur le port **uplink vers le serveur
DHCP**, pas sur le port où le client/AP est branché. Sur `switch01`, les ports
`Gi1/0/17` et `Gi1/0/48` (vers les AP, VLAN 67) sont **untrusted** — c'est correct et
attendu, c'est `Po1`/`Po2` (uplinks) qui sont trusted.

---

## Commandes de diagnostic utiles (cheat-sheet)

### Côté WLC (IOS-XE 15.2, plateforme 5760)

```
! Horloge / NTP
show clock
show ntp status
clock set <hh:mm:ss> <jour> <mois> <année>
no ntp peer <ip>

! DHCP
show ip dhcp binding
show ip dhcp pool <nom>
show ip dhcp server statistics
debug ip dhcp server packet      ! penser à "no debug ..." après

! DHCP snooping
show ip dhcp snooping
show ip dhcp snooping binding
debug ip dhcp snooping packet
debug ip dhcp snooping event

! Interfaces / port-channel
show interfaces <if> status
show interfaces <if> switchport
show interfaces Port-channel1
show etherchannel summary
clear counters <if>

! AP / CAPWAP — commandes "show capwap ..." et "debug capwap console/events"
! type AireOS NE FONCTIONNENT PAS sur cette plateforme IOS-XE. Utiliser plutôt :
show ap summary
debug capwap ap events
debug capwap ap error

! Certificats
show crypto pki certificates
show crypto pki certificates TP-self-signed-XXXXXXXXXX
```

### Côté AP (AireOS, AP3G2 — `ap3g2-k9w8-mx`)

Login par défaut testé avec succès : `Cisco` / `Cisco` (ou `lanets` / mot de passe
configuré via `ap mgmtuser` sur le WLC, ex. `Bacon123`).

```
! Horloge
clock set <hh:mm:ss> <jour> <mois> <année>

! CAPWAP / discovery
show capwap ip config
show capwap client config
show version

! Logs en direct au boot (très verbeux, montre les VRAIES erreurs DTLS/PKI
! qu'on ne voit PAS côté WLC)
```

### Bootloader AP (accès console, sans mot de passe requis)

Accessible en interrompant le boot normal (touche selon modèle). Utile si mot de
passe console/enable inconnu.

```
ap: dir flash:
ap: erase /all      ! reset usine complet — repart avec discovery CAPWAP propre
ap: boot
```

---

## Architecture VLAN de référence (post-refactor SummerCamp 2026)

| VLAN | Nom     | Subnet        | Rôle                                             | DHCP                                                                 |
| ---- | ------- | ------------- | ------------------------------------------------ | -------------------------------------------------------------------- |
| 66   | CLIENT  | 10.110.0.0/16 | Trafic clients wifi (joueurs)                    | Externe (Kea)                                                        |
| 67   | AP-MGMT | 10.120.0.0/16 | Management AP + ap-manager + wireless management | Local sur le WLC, pool `AP-MGMT`, **snooping désactivé sur ce VLAN** |

- `wireless management interface Vlan67`
- `wireless ap-manager interface Vlan67`
- `wlan TisTheLan 1 Lan_ETS` → `client vlan 66`
- `ap group LanETS` → `wlan 1` (WLAN-ID, pas VLAN!)
- DHCP option 43 sur le pool `AP-MGMT` : `option 43 hex f104.0a78.0201` (pointe vers
  `10.120.2.1`, l'IP ap-manager du WLC)

---

## Checklist de démarrage pour un événement (à faire dans l'ordre)

1. Démarrer le WLC, attendre qu'il soit up.
2. **Immédiatement** : `clock set 12:00:00 1 jan 2018` (ou autre date pré-2025).
3. Vérifier `show ntp status` — NTP doit être désactivé / non synchronisé.
4. Vérifier `show ip dhcp snooping` — VLAN 67 ne doit PAS être dans la liste
   "operational".
5. Vérifier `show running-config interface Vlan67`, `Port-channel1`, etc. contre ce
   document si des doutes.
6. Brancher les AP, attendre ~2-3 min par AP pour le join CAPWAP complet.
7. `show ap summary` pour confirmer le join.
8. `copy run start` une fois tout stable.
