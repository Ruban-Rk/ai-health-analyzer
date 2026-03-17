import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import pickle
import os

symptoms_data = {
    'fever': [1,0,1,1,0,1,0,1,1,0,1,0,1,0,0,1,1,0,1,0],
    'cough': [1,1,0,1,1,0,1,0,1,1,0,1,0,0,1,1,0,1,0,1],
    'headache': [0,1,1,0,1,1,0,1,0,1,1,0,0,1,1,0,1,0,1,1],
    'fatigue': [1,1,0,1,0,1,1,0,1,0,1,1,0,1,0,1,0,1,1,0],
    'sore_throat': [0,1,1,0,1,0,1,1,0,0,1,0,1,1,0,0,1,1,0,1],
    'body_ache': [1,0,1,1,0,1,0,1,1,0,0,1,1,0,1,0,1,0,1,0],
    'nausea': [0,1,0,1,1,0,1,0,0,1,1,0,1,0,1,1,0,1,0,1],
    'runny_nose': [0,1,1,0,1,1,0,0,1,1,0,1,0,1,1,0,0,1,1,0],
    'disease': [
        'Flu','Cold','Migraine','Flu','Cold','Flu','Cold','Migraine',
        'Flu','Cold','Migraine','Cold','Flu','Migraine','Cold','Flu',
        'Migraine','Cold','Flu','Cold'
    ]
}

df = pd.DataFrame(symptoms_data)
X = df.drop('disease', axis=1)
y = df['disease']

le = LabelEncoder()
y_encoded = le.fit_transform(y)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X, y_encoded)

os.makedirs('model', exist_ok=True)
with open('model/model.pkl', 'wb') as f:
    pickle.dump(model, f)
with open('model/label_encoder.pkl', 'wb') as f:
    pickle.dump(le, f)

print("Model trained and saved!")
print(f"Classes: {le.classes_}")
