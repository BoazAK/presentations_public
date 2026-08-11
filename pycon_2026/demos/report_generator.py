"""
Démo 8 : Rapport de pentest automatisé
PyCon Togo 2026

Combine les résultats des autres démos pour générer un rapport HTML propre.
Utilise Jinja2 pour le templating.
"""

import json
import os
from datetime import datetime
from collections import Counter


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de sécurité — {{ target }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0; padding: 0;
            background: #0D1117; color: #C9D1D9;
        }
        .container { max-width: 900px; margin: 0 auto; padding: 40px 20px; }
        h1 { color: #00FF41; border-bottom: 2px solid #30363D; padding-bottom: 10px; }
        h2 { color: #58A6FF; margin-top: 30px; }
        .meta { color: #8B949E; font-size: 14px; margin-bottom: 30px; }
        .card { background: #161B22; border: 1px solid #30363D; border-radius: 8px; padding: 20px; margin: 15px 0; }
        .critical { color: #FF4444; }
        .warning { color: #FFA500; }
        .ok { color: #00FF41; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { padding: 10px 15px; text-align: left; border-bottom: 1px solid #30363D; }
        th { color: #00FF41; font-weight: 600; }
        .footer { margin-top: 50px; padding-top: 20px; border-top: 1px solid #30363D; color: #8B949E; font-size: 13px; text-align: center; }
        pre { background: #0D1117; padding: 15px; border-radius: 6px; overflow-x: auto; font-size: 13px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Rapport de sécurité</h1>
        <div class="meta">
            <strong>Cible :</strong> {{ target }}<br>
            <strong>Date :</strong> {{ date }}<br>
            <strong>Analyste :</strong> {{ analyst }}
        </div>

        <h2>1. Résumé</h2>
        <div class="card">
            <p><strong>Ports ouverts :</strong> {{ open_ports_count }} ({{ open_ports_list }})</p>
            <p><strong>Headers de sécurité absents :</strong> {{ missing_headers_count }}</p>
            <p><strong>IP suspectes détectées :</strong> {{ suspicious_ips_count }}</p>
        </div>

        <h2>2. Scan de ports</h2>
        <div class="card">
            <table>
                <tr><th>Port</th><th>Service</th><th>Statut</th></tr>
                {% for port in scan_results %}
                <tr>
                    <td>{{ port.port }}</td>
                    <td>{{ port.service }}</td>
                    <td class="ok">OUVERT</td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <h2>3. Headers de sécurité</h2>
        <div class="card">
            <table>
                <tr><th>Header</th><th>Statut</th><th>Risque</th></tr>
                {% for header in header_results %}
                <tr>
                    <td>{{ header.name }}</td>
                    <td class="{{ header.css_class }}">{{ header.status }}</td>
                    <td>{{ header.risk }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <h2>4. Analyse des logs</h2>
        <div class="card">
            <table>
                <tr><th>IP</th><th>Tentatives</th></tr>
                {% for ip in log_analysis %}
                <tr>
                    <td>{{ ip.address }}</td>
                    <td class="warning">{{ ip.count }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>

        <h2>5. Recommandations</h2>
        <div class="card">
            <ul>
                {% for rec in recommendations %}
                <li>{{ rec }}</li>
                {% endfor %}
            </ul>
        </div>

        <div class="footer">
            Rapport généré automatiquement avec Python — PyCon Togo 2026
        </div>
    </div>
</body>
</html>
"""


def generate_report(
    target: str,
    scan_results: list[dict],
    header_results: list[dict],
    log_analysis: list[dict],
    recommendations: list[str],
    output_path: str = "data/report.html",
):
    template = HTML_TEMPLATE

    template = template.replace("{{ target }}", target)
    template = template.replace("{{ date }}", datetime.now().strftime("%d/%m/%Y %H:%M"))
    template = template.replace("{{ analyst }}", os.environ.get("USER", "Analyste"))

    open_ports = [r["port"] for r in scan_results]
    template = template.replace("{{ open_ports_count }}", str(len(open_ports)))
    template = template.replace("{{ open_ports_list }}", ", ".join(str(p) for p in open_ports) if open_ports else "Aucun")

    missing = sum(1 for h in header_results if h["status"] == "ABSENT")
    template = template.replace("{{ missing_headers_count }}", str(missing))
    template = template.replace("{{ suspicious_ips_count }}", str(len(log_analysis)))

    scan_rows = ""
    for r in scan_results:
        scan_rows += f'<tr><td>{r["port"]}</td><td>{r["service"]}</td><td class="ok">OUVERT</td></tr>\n'
    template = template.replace("{% for port in scan_results %}", "<!-- SCAN_ROWS -->")
    template = template.replace("{% endfor %}", "<!-- /SCAN_ROWS -->")
    template = template.replace("<!-- SCAN_ROWS -->", "").replace("<!-- /SCAN_ROWS -->", "")
    template = template.replace('<tr><td>{{ port.port }}</td><td>{{ port.service }}</td><td class="ok">OUVERT</td></tr>', scan_rows.strip())

    header_rows = ""
    for h in header_results:
        css = "ok" if h["status"] == "PRESENT" else "critical"
        header_rows += f'<tr><td>{h["name"]}</td><td class="{css}">{h["status"]}</td><td>{h["risk"]}</td></tr>\n'
    template = template.replace("{% for header in header_results %}", "<!-- HEADER_ROWS -->")
    template = template.replace("{% endfor %}", "<!-- /HEADER_ROWS -->")
    template = template.replace("<!-- HEADER_ROWS -->", "").replace("<!-- /HEADER_ROWS -->", "")
    template = template.replace('<tr><td>{{ header.name }}</td><td class="{{ header.css_class }}">{{ header.status }}</td><td>{{ header.risk }}</td></tr>', header_rows.strip())

    log_rows = ""
    for ip in log_analysis:
        log_rows += f'<tr><td>{ip["address"]}</td><td class="warning">{ip["count"]}</td></tr>\n'
    template = template.replace("{% for ip in log_analysis %}", "<!-- LOG_ROWS -->")
    template = template.replace("{% endfor %}", "<!-- /LOG_ROWS -->")
    template = template.replace("<!-- LOG_ROWS -->", "").replace("<!-- /LOG_ROWS -->", "")
    template = template.replace('<tr><td>{{ ip.address }}</td><td class="warning">{{ ip.count }}</td></tr>', log_rows.strip())

    rec_rows = "\n".join(f"<li>{r}</li>" for r in recommendations)
    template = template.replace("{% for rec in recommendations %}", "<!-- REC_ROWS -->")
    template = template.replace("{% endfor %}", "<!-- /REC_ROWS -->")
    template = template.replace("<!-- REC_ROWS -->", "").replace("<!-- /REC_ROWS -->", "")
    template = template.replace("<li>{{ rec }}</li>", rec_rows)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(template)

    print(f"[✓] Rapport généré : {output_path}")
    print(f"    Ouvrez-le dans votre navigateur !")


def main():
    target = "example.com"

    scan_results = [
        {"port": 80, "service": "HTTP"},
        {"port": 443, "service": "HTTPS"},
        {"port": 22, "service": "SSH"},
        {"port": 8080, "service": "HTTP-Alt"},
    ]

    header_results = [
        {"name": "X-Frame-Options", "status": "PRESENT", "risk": "Clickjacking"},
        {"name": "Content-Security-Policy", "status": "ABSENT", "risk": "XSS"},
        {"name": "Strict-Transport-Security", "status": "PRESENT", "risk": "MITM"},
        {"name": "X-Content-Type-Options", "status": "ABSENT", "risk": "MIME sniffing"},
        {"name": "Referrer-Policy", "status": "PRESENT", "risk": "Fuites Referer"},
    ]

    log_analysis = [
        {"address": "45.33.32.156", "count": 156},
        {"address": "103.99.0.122", "count": 42},
        {"address": "61.177.172.35", "count": 23},
        {"address": "185.220.101.34", "count": 18},
        {"address": "192.168.1.100", "count": 7},
    ]

    recommendations = [
        "Ajouter un header Content-Security-Policy avec une politique stricte pour prévenir les attaques XSS.",
        "Ajouter X-Content-Type-Options: nosniff pour empêcher le MIME sniffing.",
        "Restreindre l'accès SSH aux IP de confiance uniquement (pare-feu).",
        "Mettre en place fail2ban pour bloquer automatiquement les IP après 5 tentatives échouées.",
        "Effectuer un audit complet des ports ouverts et désactiver les services inutiles.",
    ]

    generate_report(target, scan_results, header_results, log_analysis, recommendations)


if __name__ == "__main__":
    main()
