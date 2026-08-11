"""
Démo 9 : SAST (Static Application Security Testing) minimal en Python
PyCon Togo 2026

Analyse statique de code Python pour détecter des patterns de vulnérabilités.
Utilise le module AST (Abstract Syntax Tree) de Python.

Démontre une compréhension profonde de :
- L'analyse statique de code
- L'AST et comment Python interprète le code
- Les vulnérabilités courantes dans le code Python
"""

import ast
import sys
import os
from dataclasses import dataclass, field


@dataclass
class Finding:
    rule_id: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    line: int
    message: str
    suggestion: str


class SecurityAnalyzer(ast.NodeVisitor):
    RULES = {
        "PY-SEC-001": {
            "name": "Hardcoded Secret",
            "severity": "CRITICAL",
            "patterns": [
                "password", "passwd", "secret", "api_key", "apikey",
                "token", "private_key", "aws_key", "auth_token",
                "DATABASE_URL", "REDIS_URL",
            ],
            "suggestion": "Utilisez des variables d'environnement (os.environ) ou un gestionnaire de secrets.",
        },
        "PY-SEC-002": {
            "name": "eval() ou exec() détecté",
            "severity": "CRITICAL",
            "message": "Utilisation de {func}() — injection de code possible.",
            "suggestion": "Évitez eval()/exec(). Utilisez ast.literal_eval() ou une alternative sûre.",
        },
        "PY-SEC-003": {
            "name": "pickle.loads() non sécurisé",
            "severity": "HIGH",
            "message": "pickle.loads() sur des données non fiables — exécution de code arbitraire.",
            "suggestion": "Utilisez json ou un format de sérialisation sûr. pickle = RCE.",
        },
        "PY-SEC-004": {
            "name": "subprocess avec shell=True",
            "severity": "HIGH",
            "message": "subprocess avec shell=True — injection de commandes.",
            "suggestion": "Utilisez shell=False et passez les arguments sous forme de liste.",
        },
        "PY-SEC-005": {
            "name": "Requête SQL par concaténation",
            "severity": "HIGH",
            "message": "Construction de requête SQL par formatage de string — SQL injection.",
            "suggestion": "Utilisez des requêtes paramétrées (?, %s) ou un ORM.",
        },
        "PY-SEC-006": {
            "name": "yaml.load() non sécurisé",
            "severity": "HIGH",
            "message": "yaml.load() sans SafeLoader — exécution de code arbitraire.",
            "suggestion": "Utilisez yaml.safe_load() ou yaml.load(..., Loader=yaml.SafeLoader).",
        },
        "PY-SEC-007": {
            "name": "Debug mode en production",
            "severity": "MEDIUM",
            "message": "DEBUG=True détecté — fuite d'informations en production.",
            "suggestion": "Désactivez DEBUG en production. Utilisez une variable d'environnement.",
        },
        "PY-SEC-008": {
            "name": "Hash faible (MD5/SHA1)",
            "severity": "MEDIUM",
            "message": "Utilisation d'un algorithme de hash faible ({algo}).",
            "suggestion": "Utilisez SHA-256 ou bcrypt/argon2 pour les mots de passe.",
        },
        "PY-SEC-009": {
            "name": "ssl._create_unverified_context",
            "severity": "MEDIUM",
            "message": "Vérification SSL désactivée — vulnérable au MITM.",
            "suggestion": "Ne désactivez jamais la vérification SSL en production.",
        },
        "PY-SEC-010": {
            "name": "Random non cryptographique",
            "severity": "LOW",
            "message": "Utilisation de random() pour un contexte de sécurité.",
            "suggestion": "Utilisez secrets.token_hex() ou os.urandom() pour la cryptographie.",
        },
    }

    def __init__(self):
        self.findings: list[Finding] = []
        self.current_file = ""

    def _add_finding(self, rule_id: str, rule_def: dict, line: int, extra: str = ""):
        msg = rule_def.get("message", rule_def["name"])
        if extra:
            msg = msg.format(**extra) if isinstance(extra, dict) else f"{msg} {extra}"
        self.findings.append(Finding(
            rule_id=rule_id,
            severity=rule_def["severity"],
            line=line,
            message=msg,
            suggestion=rule_def["suggestion"],
        ))

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                for pattern in self.RULES["PY-SEC-001"]["patterns"]:
                    if pattern.lower() in var_name:
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            if len(node.value.value) > 3:
                                self._add_finding("PY-SEC-001", self.RULES["PY-SEC-001"], node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in ("eval", "exec"):
            self._add_finding("PY-SEC-002", self.RULES["PY-SEC-002"], node.lineno, {"func": func_name})

        if func_name == "loads":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "pickle":
                self._add_finding("PY-SEC-003", self.RULES["PY-SEC-003"], node.lineno)

        if func_name == "call" or func_name in ("run", "Popen", "check_output", "check_call"):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self._add_finding("PY-SEC-004", self.RULES["PY-SEC-004"], node.lineno)

        if func_name == "load":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "yaml":
                has_safe_loader = any(
                    kw.arg == "Loader" for kw in node.keywords
                )
                if not has_safe_loader:
                    self._add_finding("PY-SEC-006", self.RULES["PY-SEC-006"], node.lineno)

        if func_name in ("md5", "sha1"):
            self._add_finding("PY-SEC-008", self.RULES["PY-SEC-008"], node.lineno, {"algo": func_name.upper()})

        if func_name == "_create_unverified_context":
            self._add_finding("PY-SEC-009", self.RULES["PY-SEC-009"], node.lineno)

        if func_name in ("random", "randint", "choice", "randrange"):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "random":
                self._add_finding("PY-SEC-010", self.RULES["PY-SEC-010"], node.lineno)

        self.generic_visit(node)

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Mod):
            if isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                if any(kw in node.left.value.lower() for kw in ["select", "insert", "update", "delete", "from", "where"]):
                    self._add_finding("PY-SEC-005", self.RULES["PY-SEC-005"], node.lineno)
        self.generic_visit(node)

    def visit_JoinedStr(self, node):
        source = ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
        if any(kw in source.lower() for kw in ["select ", "insert ", "update ", "delete ", " from ", " where "]):
            self._add_finding("PY-SEC-005", self.RULES["PY-SEC-005"], node.lineno)
        self.generic_visit(node)


def analyze_file(filepath: str) -> list[Finding]:
    with open(filepath, "r") as f:
        source = f.read()
    tree = ast.parse(source)
    analyzer = SecurityAnalyzer()
    analyzer.current_file = filepath
    analyzer.visit(tree)
    return analyzer.findings


def analyze_vulnerable_code():
    test_code = '''
import os
import pickle
import subprocess
import yaml
import hashlib
import random
import ssl

API_KEY = "sk-abc123def456ghi789jkl"
DATABASE_PASSWORD = "super_secret_admin_123"
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

def dangerous_eval(user_input):
    result = eval(user_input)
    return result

def dangerous_exec(code):
    exec(code)

def load_untrusted_pickle(data):
    return pickle.loads(data)

def run_command(cmd, user_input):
    subprocess.run(cmd + " " + user_input, shell=True)

def get_user(cursor, username):
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return cursor.execute(query)

def load_yaml(data):
    config = yaml.load(data)
    return config

def weak_hash(password):
    return hashlib.md5(password.encode()).hexdigest()

def insecure_random():
    return random.randint(100000, 999999)

def no_ssl_verify():
    ctx = ssl._create_unverified_context()
    return ctx

DEBUG = True
'''
    with open("/tmp/test_vuln.py", "w") as f:
        f.write(test_code)

    findings = analyze_file("/tmp/test_vuln.py")
    return findings


def main():
    print(f"\n{'='*70}")
    print(f"🔬 SAST — Analyse Statique de Sécurité avec Python AST")
    print(f"{'='*70}")

    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        if not os.path.isfile(filepath):
            print(f"[✗] Fichier introuvable : {filepath}")
            sys.exit(1)
        findings = analyze_file(filepath)
        print(f"\n📁 Fichier analysé : {filepath}\n")
    else:
        print("\n[*] Mode démo : analyse d'un fichier de test vulnérable.\n")
        findings = analyze_vulnerable_code()

    if not findings:
        print("[✓] Aucune vulnérabilité détectée !")
        return

    severity_colors = {
        "CRITICAL": "\033[91m",
        "HIGH": "\033[93m",
        "MEDIUM": "\033[94m",
        "LOW": "\033[90m",
    }
    RESET = "\033[0m"

    print(f"{'Sévérité':>10s}  {'Règle':12s}  Ligne  Description")
    print("-" * 70)

    for f in findings:
        color = severity_colors.get(f.severity, "")
        severity = f"{color}{f.severity}{RESET}"
        print(f"{severity:>17s}  {f.rule_id:12s}  {f.line:4d}  {f.message}")

    print(f"\n{'='*70}")
    print(f"📊 Résumé : {len(findings)} vulnérabilités détectées")
    print(f"{'='*70}")

    critical = sum(1 for f in findings if f.severity == "CRITICAL")
    high = sum(1 for f in findings if f.severity == "HIGH")
    medium = sum(1 for f in findings if f.severity == "MEDIUM")
    low = sum(1 for f in findings if f.severity == "LOW")

    print(f"  🔴 CRITICAL : {critical}")
    print(f"  🟠 HIGH     : {high}")
    print(f"  🔵 MEDIUM   : {medium}")
    print(f"  ⚪ LOW      : {low}")

    print(f"\n💡 Suggestions de correction :")
    seen = set()
    for f in findings:
        if f.suggestion not in seen:
            seen.add(f.suggestion)
            print(f"  → {f.suggestion}")


if __name__ == "__main__":
    main()
