import numpy
import pandas
import spacy

from sklearn.base import ClassifierMixin, BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from spacy.lang.en import English
from xgboost import XGBClassifier


class NeedsDiagnosisModel(BaseEstimator, TransformerMixin, ClassifierMixin):
    """Model to predict needsdiagnosis flags"""

    def __init__(self, verbose=True):
        self.xgb_params = {
            "eta": 0.1,
            "max_depth": 7,
            "gamma": 1,
            "min_child_weight": 1,
            "subsample": 0.5,
            "colsample_bytree": 0.8,
            "max_bin": 256,
            "objective": "binary:logistic",
            "tree_method": "hist",
            "silent": 1,
        }
        self.clf = XGBClassifier(**self.xgb_params)
        self.le = LabelEncoder()
        self.verbose = verbose

    def preprocess(self, X, y):
        """Preprocess data

        * body, title: Tokenize input
        * needsdiagnosis: Encode labels

        """

        nlp = spacy.load("en_core_web_sm")
        parser = English()

        def _spacy_tokenizer(sentence):
            tokens = parser(sentence)
            tokens = [token for token in tokens if not token.is_stop]
            tokens = [token.lemma_ for token in tokens]
            return tokens

        self.body_tokenizer = CountVectorizer(
            tokenizer=_spacy_tokenizer, max_features=10000
        )
        self.title_tokenizer = CountVectorizer(
            tokenizer=_spacy_tokenizer, max_features=10000
        )
        self.body_tokenizer.fit(X["body"])
        self.title_tokenizer.fit(X["title"])
        body = self.body_tokenizer.transform(X["body"].values).toarray()
        title = self.title_tokenizer.transform(X["title"].values).toarray()
        X = numpy.hstack([body, title])

        needsdiagnosis = self.le.fit_transform(y["needsdiagnosis"])
        y = needsdiagnosis
        return (X, y)

    def fit(self, X, y):
        """Fit the XGBClassifier used for the model"""

        X, y = self.preprocess(X, y)
        X_train, X_eval, y_train, y_eval = train_test_split(X, y, test_size=0.3)
        eval_set = [(X_eval, y_eval)]
        self.clf.fit(
            X_train,
            y_train,
            early_stopping_rounds=10,
            eval_metric="logloss",
            eval_set=eval_set,
            verbose=self.verbose,
        )

        y_pred = self.clf.predict(X_eval)

        if self.verbose:
            print(classification_report(y_eval, y_pred))
            print(confusion_matrix(y_eval, y_pred))

        return self

    def predict(self, X):
        """Predict needsdiagnosis flags"""
        body = self.body_tokenizer.transform(X["body"].values).toarray()
        title = self.title_tokenizer.transform(X["title"].values).toarray()
        X = numpy.hstack([body, title])
        return self.clf.predict(X)

    def predict_proba(self, X):
        body = self.body_tokenizer.transform(X["body"].values).toarray()
        title = self.title_tokenizer.transform(X["title"].values).toarray()
        X = numpy.hstack([body, title])
        return self.clf.predict_proba(X)
