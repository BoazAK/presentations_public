"""
Démo 6 : Détection de phishing par Machine Learning
PyCon Togo 2026

Utilise scikit-learn pour classifier des URLs comme légitimes ou phishing.
Approche simple basée sur des n-grams de caractères.
"""

import csv
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix


def train_and_evaluate(filepath: str):
    urls = []
    labels = []

    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            urls.append(row["url"])
            labels.append(int(row["label"]))

    if len(set(labels)) < 2:
        print("[✗] Le dataset doit contenir au moins 2 classes (0 et 1).")
        return

    nb_legit = labels.count(0)
    nb_phish = labels.count(1)
    print(f"\n{'='*60}")
    print(f"🎣 Détection de Phishing — Dataset chargé")
    print(f"{'='*60}")
    print(f"URLs légitimes : {nb_legit}")
    print(f"URLs phishing  : {nb_phish}")

    X_train, X_test, y_train, y_test = train_test_split(
        urls, labels, test_size=0.3, random_state=42, stratify=labels
    )

    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 5), max_features=1000)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    model = MultinomialNB(alpha=0.1)
    model.fit(X_train_vec, y_train)

    y_pred = model.predict(X_test_vec)
    accuracy = (y_pred == y_test).mean()

    print(f"\nÉchantillons d'entraînement : {len(X_train)}")
    print(f"Échantillons de test       : {len(X_test)}")
    print(f"\n📊 Précision : {accuracy:.2%}")

    print(f"\nMatrice de confusion :")
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
    print(f"  Légitime→Légitime : {cm[0][0]:3d}  |  Légitime→Phishing : {cm[0][1]:3d}")
    print(f"  Phishing→Légitime : {cm[1][0]:3d}  |  Phishing→Phishing : {cm[1][1]:3d}")

    print(f"\nRapport de classification :")
    print(classification_report(y_test, y_pred, target_names=["Legitime", "Phishing"]))

    print("\n🧪 Test sur des URLs inconnues :")
    test_urls = [
        "https://www.google.com/search?q=python",
        "http://paypa1-secure.com/login.php?user=admin",
        "https://github.com/explore",
        "http://192.168.1.1/verify-account/",
        "https://stackoverflow.com/questions/tagged/python",
    ]
    test_vec = vectorizer.transform(test_urls)
    predictions = model.predict(test_vec)
    probs = model.predict_proba(test_vec)

    for url, pred, prob in zip(test_urls, predictions, probs):
        label = "🔴 PHISHING" if pred == 1 else "🟢 LEGITIME"
        confidence = max(prob)
        print(f"  {label} ({confidence:.1%}) → {url}")


def main():
    filepath = "data/urls.csv"
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    train_and_evaluate(filepath)


if __name__ == "__main__":
    main()
