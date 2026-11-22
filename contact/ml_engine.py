import os
import joblib
import logging

logger = logging.getLogger(__name__)

#Global model cache — loaded once, reused on every request
_model = None
#Loading the spam classifier from disk.
def load_model():
    global _model
    if _model is None:
        model_path = os.getenv('MODEL_PATH', 'models/spam_classifier_v1.joblib')
        if os.path.exists(model_path):
            _model = joblib.load(model_path)
            logger.info(f"ML model loaded from {model_path}")
        else:
            logger.warning("No ML model found. Using fallback scoring.")
            _model = None
    return _model


#Scoring a message for spam probability.
def score_message(text):
    try:
        model = load_model()
        if model is None:
            #No model trained yet
            logger.warning("No model available. Returning default score 0.0")
            return 0.0

        #Getting probability of spam
        score = model.predict_proba([text])[0][1]
        return round(float(score), 4)

    except Exception as e:
        logger.error(f"Machine Learning scoring error: {e}")
        return 0.0 

#Force reload the model from disk after retraining.
def reload_model():
    global _model
    _model = None
    return load_model()

 #Return basic info about the currently loaded model.
    model = load_model()
    if model is None:
        return {"status": "no model loaded", "ready": False}
    return {
        "status": "loaded",
        "ready": True,
        "type": type(model).__name__,
    }