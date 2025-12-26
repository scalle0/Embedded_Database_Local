#!/bin/bash
# Quick email export helper script for Microsoft 365

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Microsoft 365 Email Export Helper                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if Python script exists
if [ ! -f "export_microsoft_emails.py" ]; then
    echo -e "${RED}Error: export_microsoft_emails.py not found!${NC}"
    exit 1
fi

# Menu
echo "Select export type:"
echo "  1) Test export (100 emails)"
echo "  2) Full sent items (all time)"
echo "  3) Last 5 years sent items"
echo "  4) Last year sent items"
echo "  5) Custom date range"
echo ""
read -p "Choice [1-5]: " choice

# Get email
read -p "Enter your work email: " email_address

echo -e "${YELLOW}Enter your password (or App Password if using 2FA):${NC}"
read -s password
echo ""

case $choice in
    1)
        echo -e "${GREEN}Exporting 100 test emails...${NC}"
        python export_microsoft_emails.py \
            --method imap \
            --email "$email_address" \
            --password "$password" \
            --limit 100
        ;;
    2)
        echo -e "${GREEN}Exporting all sent items...${NC}"
        python export_microsoft_emails.py \
            --method imap \
            --email "$email_address" \
            --password "$password" \
            --folder "Sent Items"
        ;;
    3)
        current_year=$(date +%Y)
        start_year=$((current_year - 5))
        echo -e "${GREEN}Exporting sent items from $start_year to $current_year...${NC}"
        python export_microsoft_emails.py \
            --method imap \
            --email "$email_address" \
            --password "$password" \
            --folder "Sent Items" \
            --start-date "01-Jan-$start_year"
        ;;
    4)
        current_year=$(date +%Y)
        echo -e "${GREEN}Exporting sent items from $current_year...${NC}"
        python export_microsoft_emails.py \
            --method imap \
            --email "$email_address" \
            --password "$password" \
            --folder "Sent Items" \
            --start-date "01-Jan-$current_year"
        ;;
    5)
        read -p "Start date (DD-MMM-YYYY, e.g., 01-Jan-2015): " start_date
        read -p "End date (DD-MMM-YYYY, e.g., 31-Dec-2024): " end_date
        echo -e "${GREEN}Exporting sent items from $start_date to $end_date...${NC}"
        python export_microsoft_emails.py \
            --method imap \
            --email "$email_address" \
            --password "$password" \
            --folder "Sent Items" \
            --start-date "$start_date" \
            --end-date "$end_date"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Summary
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Export Complete!                                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Count exported files
total=$(find data/input/emails -name "*.eml" 2>/dev/null | wc -l | tr -d ' ')
echo -e "Total emails exported: ${BLUE}$total${NC}"
echo ""

# Show by year
echo "Emails by year:"
for year in {2015..2024}; do
    count=$(find data/input/emails -path "*/$year/*" -name "*.eml" 2>/dev/null | wc -l | tr -d ' ')
    if [ $count -gt 0 ]; then
        echo -e "  $year: ${BLUE}$count${NC} emails"
    fi
done

echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Test processing: python main.py --input data/input/emails/sent_items/2024"
echo "  2. Full processing: python main.py --input data/input/emails"
echo "  3. Search emails: streamlit run streamlit_app.py"
echo ""
