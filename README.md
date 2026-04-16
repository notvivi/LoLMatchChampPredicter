# Solo/Duo Champ Predictor

**Author:** Vilma Tomanová  

This project is a **desktop application for League of Legends draft prediction**.  
It uses a **machine learning model trained on real ranked match data** to recommend optimal champion picks based on team composition.

- Data sources: https://developer.riotgames.com/apis and https://darkintaqt.com/blog/champ-ids
- Model: https://drive.google.com/drive/folders/13cIkm6INGS5btVNQXJgnUCCGkHzkgTI2?usp=sharing

---

# Requirements

- Python 3.10+
- customtkinter
- pillow
- requests
- numpy
- joblib
- scikit-learn

Install dependencies:
```bash
pip install -r requirements.txt
```

---

# Key Features

- Champion recommendation based on draft composition  
- Real-time prediction during champion select  
- Role-based pick suggestions (TOP, JUNGLE, MIDDLE, BOTTOM, SUPPORT)  
- Uses real data collected via Riot API  
- Lightweight desktop UI (CustomTkinter)  
---

# Table of Contents

- Installation  
- Usage  
- How it works  
- Data collection  
- Model training  
- Project structure  
- Documentation  

---

# Installation



---

# Usage



---

# How to Use

1. Select your role  
2. Enter champion names into slots (press **Enter**)  
3. Fill ally and enemy team compositions  
4. Click **PREDICT**  
5. The model will suggest top 3 champions  

- Each champion can only be selected once  
- Invalid names are rejected  
- Supports partial input (e.g. "yas" → Yasuo if unique)

---

# How it Works

The application:

1. Loads champion data from Riot Data Dragon  
2. Converts selected champions into **feature vectors**  
3. Uses a trained **machine learning model**  
4. Outputs top 3 recommended champions  

### Feature Engineering

- Champion tags (Tank, Mage, Assassin, etc.)
- Team composition statistics
- Ally vs enemy differences
- Role encoding (one-hot)

---

# Data Collection

Data was collected using a **custom scraper** based on Riot API:

- Region: `EUN1`
- Queue: `RANKED_SOLO_5x5`
- Rank: `EMERALD I–IV`

Each match generates multiple records containing:

- Role
- Champion ID
- Win/loss
- Ally champions
- Enemy champions

Dataset size:
- 1500+ matches
- 10,000+ rows

---

# Model Training

The model is trained using:

- Scikit-learn (RandomForestClassifier)
- Train/Test split (80/20)
- Feature engineering from raw match data

Model output:
- Probability distribution over champions
- Top 3 recommended picks displayed in UI

# Old project links
- [Documentation structure](https://github.com/notvivi/DatabaseManagementForShop/blob/main/doc/documentation.pdf)
- [User interface](https://github.com/notvivi/HackerBankNode/tree/main/src/ui)

## Documentation
- README.md – project overview and usage
- [documentation.pdf](doc/documentation.pdf) - overall documentation (readme is shortened)
- [license](LICENSE) - used license for this project
