# Phishing Website Detection - Viva Questions and Answers

## 1. What is phishing?
Phishing is an online deception technique in which an attacker creates a misleading message or website to trick users into revealing passwords, payment information or other sensitive data.

## 2. What is the objective of this project?
The objective is to accept a raw website URL, extract measurable URL and domain characteristics, and use a trained machine-learning classifier to predict whether the URL looks phishing-like or legitimate-like.

## 3. Which dataset is used?
The project uses the PhiUSIIL Phishing URL (Website) dataset from the UCI Machine Learning Repository, dataset ID 967. It contains raw URL strings and labels, along with additional precomputed fields. This project uses the raw URL and label for training its own URL feature extractor.

## 4. What is the label mapping?
In the UCI dataset, label 0 means phishing and label 1 means legitimate. The code converts this into the project's convention: 1 = phishing and 0 = legitimate.

## 5. Why do we use the raw URL field?
The application accepts a URL typed by the user. Training on raw URLs lets the exact same feature-extraction function run during training and prediction. This avoids asking the user to enter precomputed feature codes manually.

## 6. What is URL feature extraction?
It is the process of converting a URL string into numeric measurements that a machine-learning model can use. Examples include URL length, domain length, number of subdomains, digit ratio, special-character ratio, HTTPS usage, query-parameter count and URL entropy.

## 7. Does the ML model open or visit the URL?
No. The classifier uses URL text only. Feature extraction is local and does not send a request to the target website.

## 8. What is the optional webpage inspection feature?
After the user explicitly clicks the inspection button, the app can make a small HTTP GET request to a public webpage and parse limited HTML. It displays page title, forms, password inputs, iframes, links and resources as supporting observations. These observations are not fed into the ML classifier.

## 9. Which algorithms are compared?
Logistic Regression, Decision Tree, Linear Support Vector Machine (SVM) and Gaussian Naive Bayes.

## 10. Why is this a classification problem?
The output belongs to one of two categories: phishing-like or legitimate-like. The model therefore predicts a class label rather than a continuous numerical value.

## 11. Why do we compare multiple algorithms?
Different algorithms learn different decision boundaries. Comparing them on the same training and test partitions helps select a model using measured validation performance instead of guessing.

## 12. What is precision?
Precision is the fraction of URLs predicted as phishing that are actually phishing. Higher precision means fewer legitimate URLs are incorrectly flagged.

## 13. What is recall?
Recall is the fraction of actual phishing URLs that the model correctly identifies. Higher recall means fewer phishing URLs are missed.

## 14. What is the F1-score?
F1-score is the harmonic mean of precision and recall. It is useful when both false alarms and missed phishing cases matter.

## 15. What is a confusion matrix?
It is a table comparing actual labels with predicted labels. It shows true negatives, false positives, false negatives and true positives.

## 16. Why is the data split grouped by hostname?
Many URLs can belong to the same website. If URLs from one host appear in both training and test data, the evaluation may look overly optimistic. Grouping by hostname helps keep each host in only one partition.

## 17. What is overfitting?
Overfitting occurs when a model learns noise or details specific to its training examples and performs worse on unseen data.

## 18. What does the score displayed by the app mean?
It is a model-estimated score based on learned patterns in the training dataset. It is not a guarantee, certification or definitive probability that a website is malicious.

## 19. What are the limitations of the project?
URL-only features may miss phishing pages hosted on compromised legitimate domains. The optional HTML inspection is separate and may fail if a site blocks requests, needs JavaScript, or is unavailable. Dataset performance may not match current live phishing traffic.

## 20. What safety controls exist in optional page inspection?
It only runs after a user click, limits requests to HTTP/HTTPS on standard ports, rejects local/private/reserved IP destinations, validates redirects, uses timeouts and a response-size limit, and does not execute JavaScript, submit forms, use cookies or log in. The target website may still see the user's public IP address.

## 21. What is the future scope?
Future work could add fresh threat-intelligence feeds, time-based external validation, calibrated decision thresholds, richer page-content features with a matching training dataset, and explainability methods such as SHAP or LIME.
