# -*- coding: utf-8 -*-
"""Assignment 3_Xiao Kuang.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1rgnZfpkN4qv1MXFwxstYUJfZKN2JNS3C

## Step 1: Load the dataset
"""

import pandas as pd
import numpy as np
df = pd.read_csv('reviews.csv', sep='\t')

print(df.head())

df.shape

# wordcloud function
from wordcloud import WordCloud
import matplotlib.pyplot as plt

def show_wordcloud(data, title = None, color='white'):
    wordcloud = WordCloud(
        background_color = color,
        max_words = 200,
        max_font_size = 40, 
        scale = 3,
        random_state = 42
    ).generate(str(data))

    fig = plt.figure(1, figsize = (15, 15))
    plt.axis('off')
    if title: 
        fig.suptitle(title, fontsize = 20)
        fig.subplots_adjust(top = 2.3)

    plt.imshow(wordcloud)
    plt.show()
    
# print wordcloud
show_wordcloud(df['Review'], title = "All Reviews Word Cloud")

"""## step 2: make the dataset balanced and split into training and valid set"""

# Drop the rows where column Review or RatingValue is null
data = df.dropna(subset=['Review','RatingValue'])
# create the label for review:  if the rating is 1 or 2, negative; if rating is 3, neutral; if rating is 4 or 5, positive
data["RatingValue"] = data["RatingValue"].apply(lambda x: 'Negative' if x < 3 else ('Neutral' if x < 4 else 'Positive'))

# print wordcloud
show_wordcloud(data.loc[data.RatingValue == 'Negative','Review'], title = "Negative Review Word Cloud",color='black')
show_wordcloud(data.loc[data.RatingValue == 'Neutral','Review'], title = "Neutral Review Word Cloud",color='grey')
show_wordcloud(data.loc[data.RatingValue == 'Positive','Review'], title = "Positive Review Word Cloud",color='white')

print(data["RatingValue"].value_counts())
print(data["RatingValue"].value_counts(normalize=True))

"""Since the dataset is very unbalanced, positive reviews are way more than neutral and negative.We need to drop positive ratings in order to balance the data so that you have approximately equal numbers of negative, neutral and positive ratings."""

# downsample majority class
from sklearn.utils import resample
# Separate majority and minority classes
data_majority = data[data.RatingValue=='Positive']
data_minority = pd.concat([data[data.RatingValue=='Negative'],data[data.RatingValue=='Neutral']])
# Downsample majority class
data_majority_downsampled = resample(data_majority, 
                                 replace=False,    # sample without replacement
                                 n_samples=data_minority.shape[0],     # to match minority class
                                 random_state=17)
assert data_majority_downsampled.shape== data_minority.shape      
data_balance = pd.concat([data_majority_downsampled,data_minority])
data_balance.shape

# visualization of the sentiment distribution
from plotly import graph_objs as go
temp = data_balance.groupby('RatingValue').count()['Review'].reset_index().sort_values(by='Review',ascending=False)
fig = go.Figure(go.Funnelarea(
    text =temp.RatingValue,
    values = temp.Review,
    title = {"position": "top center", "text": "Funnel-Chart of Sentiment Distribution"}
    ))
fig.show()

# feature selection
label = "RatingValue"
features = [c for c in data_balance.columns if c != label]

# split into training and valid dataset
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(data_balance[features], data_balance[label],shuffle = True, 
                                                    test_size = 0.20, random_state = 42,stratify=data_balance['RatingValue'])

# A general look at the training and valid set
training = pd.concat([X_train,y_train],axis=1)
test = pd.concat([X_test,y_test],axis=1)
print("The number of reviews in training set: ",training.shape[0])
print("The distribution of sentiment in training set:")
print(training["RatingValue"].value_counts(normalize=True))
print("*"*10)
print("The number of reviews in test set: ",test.shape[0])
print("The distribution of sentiment in valid set:")
print(test["RatingValue"].value_counts(normalize=True))

# save as training.csv and valid.csv
training.to_csv('training.csv')
test.to_csv('valid.csv')

"""## step 3: Training Data Preprocessing
Common data cleaning steps on all text:

1.Make text all lower case

2.Remove punctuation

3.Remove numerical values

4.Remove common non-sensical text

5.Tokenize text

6.Remove stop words
"""

# load the training set 
training = pd.read_csv('training.csv')

# return the wordnet object value corresponding to the POS tag
from nltk.corpus import wordnet

def get_wordnet_pos(pos_tag):
    if pos_tag.startswith('J'):
        return wordnet.ADJ
    elif pos_tag.startswith('V'):
        return wordnet.VERB
    elif pos_tag.startswith('N'):
        return wordnet.NOUN
    elif pos_tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN

# clean the text
import string
from nltk import pos_tag
from nltk.corpus import stopwords
from nltk.tokenize import WhitespaceTokenizer
from nltk.stem import WordNetLemmatizer,SnowballStemmer
import nltk
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')

def clean_text(text):
    # lower text
    text = text.lower()
    # tokenize text and remove puncutation
    text = [word.strip(string.punctuation) for word in text.split(" ")]
    # remove words that contain numbers
    text = [word for word in text if not any(c.isdigit() for c in word)]
    # remove stop words
    stop = stopwords.words('english')
    text = [x for x in text if x not in stop]
    # remove empty tokens
    text = [t for t in text if len(t) > 0]
    # pos tag text
    pos_tags = pos_tag(text)
    # lemmatize text, change verb from past tense to present tense
    text = [WordNetLemmatizer().lemmatize(t[0], get_wordnet_pos(t[1])) for t in pos_tags]
    # remove words with only one letter
    text = [t for t in text if len(t) > 1]
    # join all
    text = " ".join(text)
    return(text)

# clean training data
training["Review_Clean"] = training["Review"].apply(lambda x: clean_text(x))
training["Review_Clean"][0]

"""## step 4: feature engineering"""

# add sentiment anaylsis columns
# four columns are created, a neutrality score, a positivity score, a negativity score and an overall score that summarizes the previous scores
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
nltk.download('vader_lexicon')
def sentiment_analyzer(data,column):
  sid = SentimentIntensityAnalyzer()
  data['analysis'] = data[column].apply(lambda x: sid.polarity_scores(x))
  data = pd.concat([data.drop(['analysis'], axis=1), data['analysis'].apply(pd.Series)], axis=1)
  return data
training = sentiment_analyzer(training,'Review')
training.head()

# create doc2vec vector columns
from gensim.test.utils import common_texts
from gensim.models.doc2vec import Doc2Vec, TaggedDocument

def doc_to_vec(data,column):
  documents = [TaggedDocument(doc, [i]) for i, doc in enumerate(data[column].apply(lambda x: x.split(" ")))]
  # train a Doc2Vec model with our text data
  model = Doc2Vec(documents, vector_size=5, window=2, min_count=1, workers=4)
  # transform each document into a vector data
  doc2vec_df = data[column].apply(lambda x: model.infer_vector(x.split(" "))).apply(pd.Series)
  doc2vec_df.columns = ["doc2vec_vector_" + str(x) for x in doc2vec_df.columns]
  data = pd.concat([data, doc2vec_df], axis=1)
  return data

training = doc_to_vec(data = training,column = 'Review_Clean')
training.head()

# add tf-idfs columns
from sklearn.feature_extraction.text import TfidfVectorizer
def tf_idf(data,column):
  tfidf = TfidfVectorizer(min_df = 10)
  tfidf_result = tfidf.fit_transform(data[column]).toarray()
  tfidf_df = pd.DataFrame(tfidf_result, columns = tfidf.get_feature_names())
  tfidf_df.columns = ["word_" + str(x) for x in tfidf_df.columns]
  tfidf_df.index = data.index
  data = pd.concat([data, tfidf_df], axis=1)
  return data
training = tf_idf(training,'Review_Clean')
training.shape

# highest positive sentiment reviews (with more than 5 words)
training.sort_values("pos", ascending = False)[["Review",'RatingValue',"pos"]].head(10)
# A majority of the most positive reviews indeed correspond to some good feedbacks.

# lowest negative sentiment reviews (with more than 5 words)
print(training.sort_values("neg", ascending = False)[["Review",'RatingValue',"neg"]].head(10))
print(training['Review'][313])
# A majority of the most negative reviews indeed correspond to some bad feedbacks despite some neutral feedbacks.

# plot sentiment distribution for positive and negative reviews
import seaborn as sns
for x in ['Positive','Negative','Neutral']:
    subset = training[training['RatingValue'] == x]    
    # Draw the density plot
    if x == 'Positive':
      label = 'Positive'
    elif x == 'Neutral':
      label = 'Neutral'
    else:
      label = 'Negative'
    sns.distplot(subset['compound'], hist = False, label = label)
    plt.legend()

"""## Step 5: Train the Model(Random Forest with GridSearch)"""

from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier
# Create the parameter grid based on the results of random search 
param_grid = {
    'bootstrap': [True],
    'max_depth': [80, 90, 100, 110],
    'max_features': [2, 3],
    'min_samples_leaf': [3, 4, 5],
    'min_samples_split': [8, 10, 12],
    'n_estimators': [100, 200, 300, 1000]
}
# Create a based model
rf = RandomForestClassifier()
# Instantiate the grid search model
grid_search = GridSearchCV(estimator = rf, param_grid = param_grid, 
                          cv = 3, n_jobs = -1, verbose = 2)

# feature selection
label = "RatingValue"
ignore_cols = [label, "Review", "Review_Clean",'DatePublished','Name']
features = [c for c in training.columns if c not in ignore_cols]
# Fit the grid search to the data
grid_search.fit(training[features],training[label])

import joblib
# save the best model 
joblib.dump(grid_search.best_estimator_, 'best_model.pkl', compress = 1)

# load the best model
loaded_rf = joblib.load("best_model.pkl")
classifier = loaded_rf.fit(training[features],training[label])

loaded_rf

"""## step 6: evaluate on valid set"""

# load the test set
test = pd.read_csv('valid.csv')
# clean test data
test["Review_Clean"] = test["Review"].apply(lambda x: clean_text(x))
# feature engineering on test set 
test = sentiment_analyzer(test,'Review')
# using Doc2Vec
test = doc_to_vec(test,'Review_Clean')
# using tf_idf
test = tf_idf(test,'Review_Clean')
# apply the best model
test_features = [c for c in test.columns if c not in ignore_cols]
classifier_test = loaded_rf.fit(test[test_features],test[label])

from sklearn.metrics import confusion_matrix,accuracy_score,f1_score
y_pred = classifier_test.predict(test[test_features])
# Making the Confusion Matrix for test set
print("Accuracy on the test set is ",round(accuracy_score(test[label], y_pred),2))
print("The f1 score for the test set is",round(f1_score(test[label], y_pred, average='weighted'),2)) 
print("Confusion Matrix:")
print(pd.crosstab(test[label], y_pred))

from sklearn.metrics import plot_confusion_matrix
disp = plot_confusion_matrix(classifier, test[test_features], test[label],cmap=plt.cm.Blues,normalize=None)
disp.ax_.set_title("Confusion Matrix for Test Set")
print(disp.confusion_matrix)
plt.show()