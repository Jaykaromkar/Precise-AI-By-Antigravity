import re

class PIIVault:
    def __init__(self):
        self.mapping = {}
        self.counters = {"email": 0, "phone": 0, "money": 0, "date": 0, "name": 0, "percent": 0, "cardinal": 0}

    def mask(self, text: str) -> str:
        # 1. Mask Emails
        def replace_email(match):
            self.counters["email"] += 1
            tag = f"[EMAIL_{self.counters['email']}]"
            self.mapping[tag] = match.group(0)
            return tag
        text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', replace_email, text)
        
        # 2. Mask Phone Numbers
        def replace_phone(match):
            self.counters["phone"] += 1
            tag = f"[PHONE_{self.counters['phone']}]"
            self.mapping[tag] = match.group(0)
            return tag
        text = re.sub(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', replace_phone, text)
        
        # 3. Mask Dates (various formats)
        def replace_date(match):
            self.counters["date"] += 1
            tag = f"[DATE_{self.counters['date']}]"
            self.mapping[tag] = match.group(0)
            return tag
        text = re.sub(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}', replace_date, text)

        # 4. Mask Money
        def replace_money(match):
            self.counters["money"] += 1
            tag = f"[MONEY_{self.counters['money']}]"
            self.mapping[tag] = match.group(0)
            return tag
        # Matches $1,000, $26.3 billion, 2,075) $
        text = re.sub(r'(?:\$\s?\d+(?:,\d{3})*(?:\.\d+)?(?:\s+(?:million|billion|trillion))?|\d+(?:,\d{3})*(?:\.\d+)?\)?\s*\$)', replace_money, text)

        # 5. Mask Percentages
        def replace_percent(match):
            self.counters["percent"] += 1
            tag = f"[PERCENT_{self.counters['percent']}]"
            self.mapping[tag] = match.group(0)
            return tag
        text = re.sub(r'\d+(?:\.\d+)?\s*%', replace_percent, text)

        # 6. Mask Cardinals (Numbers and Word Numbers)
        def replace_cardinal(match):
            self.counters["cardinal"] += 1
            tag = f"[CARDINAL_{self.counters['cardinal']}]"
            self.mapping[tag] = match.group(0)
            return tag
        text = re.sub(r'(?i)\b(?:\d+(?:,\d{3})*(?:\.\d+)?(?:k|m|b)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|hundred|thousand|million|billion|trillion|thousands|millions|billions)\b', replace_cardinal, text)

        # 7. Mask Potential Names (Heuristic: Title Case names followed by Mr./Ms./Dr.)
        def replace_name(match):
            self.counters["name"] += 1
            tag = f"[NAME_{self.counters['name']}]"
            self.mapping[tag] = match.group(0)
            return tag
        text = re.sub(r'(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', replace_name, text)
        
        return text
