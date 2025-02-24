import imaplib
import email
from email.header import decode_header
import re
from bs4 import BeautifulSoup


class EmailExtractorUtils:
    IMAP_SERVER_MAP = {
        "gmx": "imap.gmx.com",
        "poczta": "imap.poczta.onet.pl",
        "rambler": "imap.rambler.ru"
    }

    IMAP_PORT = 993

    @staticmethod
    def connect_to_gmx(email: str, email_password: str):
        """Establish a connection to GMX's IMAP server."""
        try:
            if "poczta" in email:
                server = EmailExtractorUtils.IMAP_SERVER_MAP["poczta"]
            elif "rambler" in email:
                server = EmailExtractorUtils.IMAP_SERVER_MAP["rambler"]
            elif "gmx" in email:
                server = EmailExtractorUtils.IMAP_SERVER_MAP["gmx"]
            else:
                raise ValueError("Unsupported email provider.")
            mail = imaplib.IMAP4_SSL(server, EmailExtractorUtils.IMAP_PORT)
            mail.login(email, email_password)
            mail.select("INBOX")
            return mail
        except Exception as e:
            print(f"Error connecting to GMX email: {e}")
            return None

    @staticmethod
    def extract_verification_code_from_html(html_content):
        """Extracts the 6-digit verification code from the HTML email body."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            possible_code = soup.find_all("p", style=re.compile("font-weight:bold;font-size:32px;"))

            for tag in possible_code:
                match = re.search(r"\b\d{6}\b", tag.get_text())
                if match:
                    return match.group(0)

            return None
        except Exception as e:
            print(f"Error extracting verification code: {e}")
            return None

    @staticmethod
    def fetch_email_with_verification(mail):
        """Fetches the first email containing 'Login verification' and extracts the code."""
        try:
            result, data = mail.search(None, "ALL")
            email_ids = data[0].split()

            if not email_ids:
                print("No emails found.")
                return None

            for email_id in reversed(email_ids):
                result, msg_data = mail.fetch(email_id, "(RFC822)")

                if result != "OK":
                    print("Failed to fetch email.")
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding or "utf-8")
                        from_email = msg.get("From")
                        body = None

                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                content_disposition = str(part.get("Content-Disposition"))
                                if content_type == "text/html" and "attachment" not in content_disposition:
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                        if body and "login verification" in body.lower():
                            verification_code = EmailExtractorUtils.extract_verification_code_from_html(body)
                            if verification_code:
                                print(f"✅ Found 'Login verification' email with code: {verification_code}")
                                print(f"Subject: {subject}")
                                print(f"From: {from_email}")
                                print(f"Verification Code: {verification_code}")
                                return verification_code

            print("No email containing 'Login verification' found.")
            return None
        except Exception as e:
            print(f"Error fetching emails: {e}")
            return None

    @staticmethod
    def get_code(email: str, email_password: str):
        mail_client = EmailExtractorUtils.connect_to_gmx(email, email_password)
        if mail_client:
            verification_code = EmailExtractorUtils.fetch_email_with_verification(mail_client)
            if verification_code:
                print(f"🔑 Verification Code: {verification_code}")
            mail_client.logout()
            return verification_code
        return None
