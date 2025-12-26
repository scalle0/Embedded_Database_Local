#!/usr/bin/env python3
"""
Export emails from Microsoft 365 to .eml files for processing.

Supports two methods:
1. IMAP (recommended for most users)
2. Microsoft Graph API (requires app registration)

Usage:
    python export_microsoft_emails.py --method imap
    python export_microsoft_emails.py --method graph
"""

import argparse
import email
import imaplib
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import json


class EmailExporter:
    """Base class for email exporters."""

    def __init__(self, output_dir: str = "data/input/emails"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.exported_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def sanitize_filename(self, text: str, max_length: int = 100) -> str:
        """Create safe filename from text."""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, '_')

        # Limit length
        if len(text) > max_length:
            text = text[:max_length]

        return text.strip()

    def save_email(self, email_data: bytes, metadata: dict, folder: str = "sent"):
        """Save email as .eml file."""
        try:
            # Parse email
            msg = email.message_from_bytes(email_data)

            # Extract date
            date_str = msg.get('Date', '')
            try:
                date = email.utils.parsedate_to_datetime(date_str)
                year = date.year
                month = f"{date.month:02d}"
            except:
                year = "unknown"
                month = "00"

            # Extract subject
            subject = msg.get('Subject', 'no_subject')
            subject = self.sanitize_filename(subject, 50)

            # Create directory structure
            year_dir = self.output_dir / folder / str(year) / month
            year_dir.mkdir(parents=True, exist_ok=True)

            # Create unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{timestamp}_{subject}.eml"
            filepath = year_dir / filename

            # Save .eml file
            with open(filepath, 'wb') as f:
                f.write(email_data)

            self.exported_count += 1
            print(f"✓ Exported: {subject} ({year}/{month})")

        except Exception as e:
            self.error_count += 1
            print(f"✗ Error saving email: {e}")

    def print_summary(self):
        """Print export summary."""
        print("\n" + "="*60)
        print("EXPORT SUMMARY")
        print("="*60)
        print(f"✓ Exported: {self.exported_count} emails")
        print(f"⊘ Skipped:  {self.skipped_count} emails")
        print(f"✗ Errors:   {self.error_count} emails")
        print(f"📁 Location: {self.output_dir}")
        print("="*60)


class IMAPExporter(EmailExporter):
    """Export emails via IMAP (recommended for Microsoft 365)."""

    def __init__(self, output_dir: str = "data/input/emails"):
        super().__init__(output_dir)
        self.imap = None

    def connect(self, email_address: str, password: str,
                server: str = "outlook.office365.com", port: int = 993):
        """Connect to IMAP server."""
        try:
            print(f"Connecting to {server}:{port}...")
            self.imap = imaplib.IMAP4_SSL(server, port)

            print(f"Logging in as {email_address}...")
            self.imap.login(email_address, password)

            print("✓ Connected successfully!")
            return True

        except Exception as e:
            print(f"✗ Connection failed: {e}")
            print("\nTroubleshooting:")
            print("1. Enable IMAP in Outlook settings")
            print("2. Use an App Password if 2FA is enabled")
            print("3. Check firewall/network settings")
            return False

    def list_folders(self) -> List[str]:
        """List available email folders."""
        if not self.imap:
            return []

        try:
            _, folders = self.imap.list()
            folder_names = []
            for folder in folders:
                # Decode folder name
                parts = folder.decode().split(' "/" ')
                if len(parts) > 1:
                    folder_name = parts[1].strip('"')
                    folder_names.append(folder_name)
            return folder_names
        except Exception as e:
            print(f"Error listing folders: {e}")
            return []

    def export_folder(self, folder_name: str = "Sent Items",
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     limit: Optional[int] = None):
        """
        Export emails from a specific folder.

        Args:
            folder_name: Name of folder (e.g., "Sent Items", "Inbox")
            start_date: Start date in format "DD-MMM-YYYY" (e.g., "01-Jan-2015")
            end_date: End date in format "DD-MMM-YYYY"
            limit: Maximum number of emails to export
        """
        if not self.imap:
            print("Not connected to IMAP server")
            return

        try:
            # Select folder
            print(f"\nSelecting folder: {folder_name}")
            status, count = self.imap.select(f'"{folder_name}"')

            if status != 'OK':
                print(f"✗ Could not open folder: {folder_name}")
                return

            total_emails = int(count[0])
            print(f"Found {total_emails} emails in {folder_name}")

            # Build search criteria
            search_criteria = "ALL"
            if start_date and end_date:
                search_criteria = f'(SINCE "{start_date}" BEFORE "{end_date}")'
            elif start_date:
                search_criteria = f'SINCE "{start_date}"'
            elif end_date:
                search_criteria = f'BEFORE "{end_date}"'

            # Search for emails
            print(f"Searching with criteria: {search_criteria}")
            _, message_numbers = self.imap.search(None, search_criteria)

            email_ids = message_numbers[0].split()
            total_to_export = len(email_ids)

            if limit:
                email_ids = email_ids[:limit]
                print(f"Limiting to first {limit} emails")

            print(f"Exporting {len(email_ids)} emails...")

            # Export each email
            for i, email_id in enumerate(email_ids, 1):
                try:
                    # Fetch email
                    _, msg_data = self.imap.fetch(email_id, '(RFC822)')
                    email_data = msg_data[0][1]

                    # Save email
                    metadata = {
                        'folder': folder_name,
                        'email_id': email_id.decode()
                    }
                    self.save_email(email_data, metadata, folder=folder_name.lower().replace(' ', '_'))

                    # Progress
                    if i % 10 == 0:
                        print(f"Progress: {i}/{len(email_ids)} ({i*100//len(email_ids)}%)")

                except Exception as e:
                    print(f"Error exporting email {email_id}: {e}")
                    self.error_count += 1

        except Exception as e:
            print(f"✗ Error exporting folder: {e}")

    def disconnect(self):
        """Disconnect from IMAP server."""
        if self.imap:
            try:
                self.imap.close()
                self.imap.logout()
                print("✓ Disconnected")
            except:
                pass


class GraphAPIExporter(EmailExporter):
    """Export emails via Microsoft Graph API (requires app registration)."""

    def __init__(self, output_dir: str = "data/input/emails"):
        super().__init__(output_dir)
        self.access_token = None

    def authenticate(self, client_id: str, client_secret: str, tenant_id: str):
        """Authenticate with Microsoft Graph API."""
        try:
            import requests

            # Get access token
            url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

            data = {
                'client_id': client_id,
                'client_secret': client_secret,
                'scope': 'https://graph.microsoft.com/.default',
                'grant_type': 'client_credentials'
            }

            response = requests.post(url, data=data)
            response.raise_for_status()

            self.access_token = response.json()['access_token']
            print("✓ Authenticated with Microsoft Graph API")
            return True

        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            print("\nTo use Graph API:")
            print("1. Register app at https://portal.azure.com")
            print("2. Add Mail.Read permission")
            print("3. Get Client ID, Secret, and Tenant ID")
            return False

    def export_user_emails(self, user_email: str, folder: str = "sentitems",
                          limit: Optional[int] = None):
        """Export emails using Graph API."""
        if not self.access_token:
            print("Not authenticated")
            return

        try:
            import requests

            # Build API URL
            url = f"https://graph.microsoft.com/v1.0/users/{user_email}/mailFolders/{folder}/messages"

            if limit:
                url += f"?$top={limit}"

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            print(f"Fetching emails from {folder}...")

            while url:
                response = requests.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                messages = data.get('value', [])

                for msg in messages:
                    # Get full email in MIME format
                    msg_id = msg['id']
                    mime_url = f"https://graph.microsoft.com/v1.0/users/{user_email}/messages/{msg_id}/$value"

                    mime_response = requests.get(mime_url, headers=headers)

                    if mime_response.status_code == 200:
                        metadata = {
                            'folder': folder,
                            'message_id': msg_id
                        }
                        self.save_email(mime_response.content, metadata, folder)

                # Check for next page
                url = data.get('@odata.nextLink')

                if limit and self.exported_count >= limit:
                    break

        except Exception as e:
            print(f"✗ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Export Microsoft 365 emails to .eml format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export sent emails via IMAP (interactive)
  python export_microsoft_emails.py --method imap

  # Export with date range
  python export_microsoft_emails.py --method imap --start-date "01-Jan-2020" --end-date "31-Dec-2024"

  # Export limited number for testing
  python export_microsoft_emails.py --method imap --limit 100

  # Use Graph API (requires app registration)
  python export_microsoft_emails.py --method graph --client-id YOUR_ID --client-secret YOUR_SECRET --tenant-id YOUR_TENANT
        """
    )

    parser.add_argument('--method', choices=['imap', 'graph'], default='imap',
                       help='Export method (default: imap)')
    parser.add_argument('--email', help='Your email address')
    parser.add_argument('--password', help='Your password or app password')
    parser.add_argument('--folder', default='Sent Items',
                       help='Folder to export (default: Sent Items)')
    parser.add_argument('--start-date', help='Start date (DD-MMM-YYYY, e.g., 01-Jan-2015)')
    parser.add_argument('--end-date', help='End date (DD-MMM-YYYY)')
    parser.add_argument('--limit', type=int, help='Limit number of emails to export')
    parser.add_argument('--output', default='data/input/emails',
                       help='Output directory (default: data/input/emails)')

    # Graph API specific
    parser.add_argument('--client-id', help='Azure App Client ID (for Graph API)')
    parser.add_argument('--client-secret', help='Azure App Client Secret')
    parser.add_argument('--tenant-id', help='Azure Tenant ID')

    args = parser.parse_args()

    if args.method == 'imap':
        exporter = IMAPExporter(args.output)

        # Get credentials
        email_address = args.email or input("Enter your email address: ")
        password = args.password or input("Enter your password (or app password): ")

        # Connect
        if not exporter.connect(email_address, password):
            sys.exit(1)

        # List available folders
        print("\nAvailable folders:")
        folders = exporter.list_folders()
        for i, folder in enumerate(folders, 1):
            print(f"  {i}. {folder}")

        # Export
        exporter.export_folder(
            folder_name=args.folder,
            start_date=args.start_date,
            end_date=args.end_date,
            limit=args.limit
        )

        exporter.disconnect()
        exporter.print_summary()

    elif args.method == 'graph':
        if not all([args.client_id, args.client_secret, args.tenant_id, args.email]):
            print("Error: Graph API requires --client-id, --client-secret, --tenant-id, and --email")
            sys.exit(1)

        exporter = GraphAPIExporter(args.output)

        if exporter.authenticate(args.client_id, args.client_secret, args.tenant_id):
            exporter.export_user_emails(
                user_email=args.email,
                folder='sentitems',
                limit=args.limit
            )
            exporter.print_summary()


if __name__ == '__main__':
    main()
