import re

class PIIVault:
    def __init__(self):
        self.mapping = {}
        self.counters = {"EMAIL": 0, "PHONE": 0, "MONEY": 0}

    def mask(self, text: str) -> str:
        def replace_email(match):
            self.counters["EMAIL"] += 1
            tag = f"[EMAIL_{self.counters['EMAIL']}]"
            self.mapping[tag] = match.group(0)
            return tag
            
        text = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', replace_email, text)
        
        def replace_phone(match):
            self.counters["PHONE"] += 1
            tag = f"[PHONE_{self.counters['PHONE']}]"
            self.mapping[tag] = match.group(0)
            return tag
            
        text = re.sub(r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}', replace_phone, text)
        
        def replace_money(match):
            self.counters["MONEY"] += 1
            tag = f"[MONEY_{self.counters['MONEY']}]"
            self.mapping[tag] = match.group(0)
            return tag
            
        text = re.sub(r'\$\s?\d+(?:,\d{3})*(?:\.\d{2})?', replace_money, text)
        
        return text
