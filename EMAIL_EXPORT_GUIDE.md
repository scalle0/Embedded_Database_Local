# Microsoft 365 Email Export Guide

Exporteer je werk emails van Microsoft 365 naar het document processing systeem.

## Optie 1: IMAP Export (Aanbevolen - Eenvoudig)

### Voorbereiding

**1. Schakel IMAP in voor je Microsoft 365 account**:
- Ga naar https://outlook.office.com/mail/options/mail/accounts
- Klik op "POP and IMAP"
- Schakel IMAP in
- Sla de wijzigingen op

**2. Genereer een App Password (als je 2FA hebt)**:
- Ga naar https://account.microsoft.com/security
- Klik op "App passwords"
- Genereer een nieuw app password
- Bewaar dit wachtwoord (je ziet het maar één keer!)

### Gebruik

**Basis export (alle verzonden emails)**:
```bash
python export_microsoft_emails.py --method imap
```

Je wordt gevraagd om:
- Email adres
- Wachtwoord (of app password)

**Export met datum bereik (bv. laatste 10 jaar)**:
```bash
python export_microsoft_emails.py \
  --method imap \
  --email jouw.naam@bedrijf.com \
  --folder "Sent Items" \
  --start-date "01-Jan-2015" \
  --end-date "31-Dec-2024"
```

**Test eerst met beperkt aantal**:
```bash
python export_microsoft_emails.py \
  --method imap \
  --email jouw.naam@bedrijf.com \
  --limit 100
```

**Export andere folders** (inbox, archive, etc.):
```bash
# Het script toont alle beschikbare folders
python export_microsoft_emails.py --method imap

# Je kunt dan kiezen uit:
# - Sent Items
# - Inbox
# - Archive
# - Deleted Items
# etc.
```

### Output Structuur

Emails worden geëxporteerd naar:
```
data/input/emails/
├── sent_items/
│   ├── 2015/
│   │   ├── 01/
│   │   │   ├── 20150115_143052_project_update.eml
│   │   │   └── 20150120_091234_meeting_notes.eml
│   │   ├── 02/
│   │   └── ...
│   ├── 2016/
│   └── ...
└── inbox/
    └── ...
```

## Optie 2: Microsoft Graph API (Geavanceerd)

Voor grote volumes of geautomatiseerde exports.

### Setup

**1. Registreer een Azure App**:
- Ga naar https://portal.azure.com
- Navigate to "Azure Active Directory" → "App registrations"
- Klik "New registration"
- Naam: "Email Exporter"
- Klik "Register"

**2. Configureer Permissions**:
- Ga naar "API permissions"
- Klik "Add a permission"
- Kies "Microsoft Graph" → "Application permissions"
- Zoek en selecteer: `Mail.Read`
- Klik "Grant admin consent"

**3. Maak Client Secret**:
- Ga naar "Certificates & secrets"
- Klik "New client secret"
- Beschrijving: "Email Export"
- Bewaar de **Value** (secret)

**4. Noteer credentials**:
- Client ID (Application ID)
- Client Secret (Value uit stap 3)
- Tenant ID (Directory ID)

### Gebruik

```bash
python export_microsoft_emails.py \
  --method graph \
  --email jouw.naam@bedrijf.com \
  --client-id "YOUR_CLIENT_ID" \
  --client-secret "YOUR_CLIENT_SECRET" \
  --tenant-id "YOUR_TENANT_ID"
```

## Tips & Best Practices

### Performance

**Voor grote volumes (>10,000 emails)**:
1. Export in batches per jaar:
```bash
for year in {2015..2024}; do
  python export_microsoft_emails.py \
    --method imap \
    --email jouw.naam@bedrijf.com \
    --start-date "01-Jan-$year" \
    --end-date "31-Dec-$year"
done
```

2. Run export 's nachts (kan uren duren voor 10 jaar emails)

3. Check progress in real-time:
```bash
# In een andere terminal
watch -n 5 'find data/input/emails -name "*.eml" | wc -l'
```

### Privacy & Beveiliging

**Gevoelige emails**:
- Het systeem verwerkt alles lokaal
- Geen data wordt naar externe servers gestuurd (behalve voor embeddings)
- Overweeg om gevoelige folders uit te sluiten

**Credentials opslaan** (optioneel voor herhaalde exports):
```bash
# Maak een .env bestand
cat >> .env << EOF
WORK_EMAIL=jouw.naam@bedrijf.com
WORK_EMAIL_PASSWORD=your_app_password_here
EOF

# Gebruik in script
python export_microsoft_emails.py \
  --method imap \
  --email $WORK_EMAIL \
  --password $WORK_EMAIL_PASSWORD
```

### Troubleshooting

**"Authentication failed"**:
- Check of IMAP enabled is
- Gebruik App Password bij 2FA
- Controleer firewall/VPN settings

**"Folder not found"**:
- Folder namen zijn taal-specifiek
- In Nederlands: "Verzonden items" i.p.v. "Sent Items"
- Gebruik `--folder "Verzonden items"`

**"Connection timeout"**:
- Bedrijfsnetwerk blokkeert mogelijk IMAP (poort 993)
- Probeer vanaf thuis/andere netwerk
- Of gebruik Graph API methode

**"Too many requests"** (rate limiting):
- Microsoft heeft rate limits op IMAP
- Voeg delays toe tussen batches
- Reduceer parallel connections

## Na Export: Verwerken

**1. Controleer geëxporteerde emails**:
```bash
# Aantal emails
find data/input/emails -name "*.eml" | wc -l

# Overzicht per jaar
for year in {2015..2024}; do
  count=$(find data/input/emails -path "*/$year/*" -name "*.eml" | wc -l)
  echo "$year: $count emails"
done
```

**2. Test met kleine batch**:
```bash
# Verwerk alleen 2024 emails eerst
python main.py --input data/input/emails/sent_items/2024
```

**3. Volledige verwerking**:
```bash
# Verwerk alle emails (kan lang duren!)
python main.py --input data/input/emails

# Of in achtergrond
nohup python main.py --input data/input/emails > email_processing.log 2>&1 &
```

**4. Zoeken in je emails**:
```bash
streamlit run streamlit_app.py

# Zoek naar:
# - "emails naar John over budget"
# - "correspondentie met Diana in 2020"
# - "project X status updates"
# - "emails met bijlagen over contract"
```

## Geschatte Tijden

| Volume | Export Tijd | Processing Tijd | Totaal |
|--------|-------------|-----------------|--------|
| 1,000 emails | ~10 min | ~15 min | ~25 min |
| 10,000 emails | ~1-2 uur | ~2-3 uur | ~4-5 uur |
| 50,000 emails | ~5-8 uur | ~10-15 uur | ~20 uur |
| 100,000 emails | ~12-16 uur | ~24-36 uur | ~2 dagen |

**Tips**:
- Run export overnight
- Processing kan parallel (gebruik `--parallel`)
- Embeddings cache helpt bij re-processing

## Kosten (Gemini API)

Voor 10 jaar emails (~50,000 emails, avg 500 tokens each):

- **Embeddings**: 50,000 emails × 500 tokens = 25M tokens
- **Gemini Free Tier**: 1,500 requests/dag (embedding)
- **Tijd**: ~33 dagen binnen free tier
- **Of betaald**: ~$0 (embeddings zijn gratis in Gemini)

**OCR kosten**: Alleen voor email attachments (images)

## Voorbeeld Complete Workflow

```bash
# 1. Export laatste 5 jaar werk emails
python export_microsoft_emails.py \
  --method imap \
  --email steven.callens@bedrijf.com \
  --start-date "01-Jan-2020" \
  --end-date "31-Dec-2024" \
  --folder "Sent Items"

# 2. Check output
find data/input/emails -name "*.eml" | wc -l
# Output: 12,450 emails

# 3. Test met recent jaar
python main.py --input data/input/emails/sent_items/2024
# Processing ~2,500 emails...

# 4. Verwerk alles
nohup python main.py --input data/input/emails > processing.log 2>&1 &

# 5. Monitor progress
tail -f processing.log
tail -f logs/pipeline.log

# 6. Search when done
streamlit run streamlit_app.py
```

## Support

Voor problemen:
- Check logs: `logs/pipeline.log`
- Email specifieke errors: `data/failed/`
- Microsoft 365 status: https://status.office365.com/

Voor vragen over het script:
- Zie code comments in `export_microsoft_emails.py`
- Test eerst met `--limit 10`
