from pkg_resources import resource_filename
import os
import enchant
import requests
import Kkit
import json
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
import spacy
import logging
from . import Probase
from . import Concepts
import math
from matplotlib import pyplot as plt
import numpy as np

stops = stopwords.words('english')

default_concepts_config = {"num": 20, "cache_path": "./cache/MCG", "probase": None}

key_concepts = ["plant", "food", "crop", "oil", "flavor", "flavours", "flavoring", "taste", "food quality", "organ", "acid", "ingredient", "scent", "drink", "beverage", "phenolic compound", "aromatic compound"]

def log(log_file, messege):
    logging.basicConfig(filename=log_file, format="%(message)s", level=logging.INFO)
    logging.INFO(messege)

class my_enchant_Dict:
    def __init__(self, enchant_dic):
        self.dict = enchant_dic
    def check(self, word_or_phrase):
        bool_list = [self.dict.check(i) for i in word_or_phrase.split(" ")]
        if False in bool_list:
            return False
        else:
            return True

def init_enchant_Dict(dic="en", extra_legal_voca=True):
    # initialize enchant spell dictionary
    # parameter:
    # dic: enchant Dcit language such as en, en_US, etc.
    if extra_legal_voca:
        voca_path = os.path.join(resource_filename(__name__, "data"), "legal_voca.txt")
        enchant_dic = enchant.DictWithPWL(dic, voca_path)
    else:
        enchant_dic = enchant.Dict(dic)
    return my_enchant_Dict(enchant_dic)

def init_probase(path, binary=False):
    if binary:
        probase = Kkit.load(path)
    else:
        probase = Probase.ProbaseConcept(path)
    return probase

def init_spacy_nlp(model="en_core_web_lg"):
    nlp = spacy.load(model)
    # if phrase:
    #     nlp.add_pipe("textrank")
    return nlp

def get_lexical_file_name(single_token, pos=wn.NOUN):
    lexname_list = [j.lexname() for j in wn.synsets(single_token,pos=pos)]
    return lexname_list

def get_concept_prob(word, num, cache_path = "./cache/MCG", probase = None) -> dict:
    if probase == None: #use web
        if cache_path: # try to load cache
            cache_list = []
            try:
                cache_list = os.listdir(cache_path)
            except:
                os.makedirs(cache_path)
            if "%s_%d"%(word,num) in cache_list:
                res = Kkit.load(os.path.join(cache_path, "%s_%d"%(word,num)))
                return res
        link = requests.get("https://concept.research.microsoft.com/api/Concept/ScoreByProb?instance=%s&topK=%d"%(word, num), verify=False)
        if link.status_code == 200:
            res = json.loads(link.text)
            if cache_path: # try to store cache
                Kkit.store(os.path.join(cache_path,"%s_%d"%(word,num)),res)
            return res
        else:
            raise Exception("code: %d"%link.status_code)
    else: #use local model
        res = {}
        concept_list = probase.conceptualize(word, score_method="likelihood")[:num]
        total = 0
        for i in concept_list:
            total+=i[1]
        for i in concept_list:
            res[i[0]] = i[1]/total
        return res

def build_key_concept_chain(word, layers, cache_path = "./cache/MCG", probase = None):
    paths = []
    paths_new = []
    root = Concepts.Node(word, 1)
    Concepts.build_concept_tree(root, layers, 0, cache_path, probase)
    Concepts.deep_search_key_concept(root, [], paths)
    for path in paths:
        temp = []
        for i in path:
            temp.append(i)
            if i in key_concepts:
                break
        if temp not in paths_new:
            paths_new.append(temp)
    return paths_new

def coverage(test_list, sdandart_DF):
    pass

def check(token, A_list):
    # example: drink in ["alcohol drink", "rice"]
    x = [i.split(" ") for i in A_list]
    y = []
    for i in x:
        y.append(i[-1])
        try:
            y.append(" ".join(i[-2:]))
        except:
            pass
        try:
            y.append(" ".join(i[-3:]))
        except:
            pass
    if token in y:
        return True
    else:
        return False

def add_star(string):
    if string.endswith(" "):
        return string.rstrip(" ")+"*"+" "
    else:
        return string+"*"

def visual_key_concept_statistics(json_dic, n_col_limit=3):
    num = len(json_dic.keys()) - 1
    if num<=n_col_limit:
        row = 1
        col = num
    else:
        row = math.ceil(num/n_col_limit)
        col = n_col_limit
    for i, (k, v) in enumerate(json_dic.items()):
        if k!="empty_concepts":
            x = [i["lemma"] for i in v]
            y = [i["count"] for i in v]
            plt.subplot(row, col, i)
            plt.bar(x, y)
            plt.title(k)

def ndarray2string(ndarray):
    return str(ndarray.dtype)+":"+np.array2string(ndarray, separator=",", threshold=np.inf).strip("[").strip("]")

def string2ndarray(ndarray_string):
    dtype_value = ndarray_string.split(":")
    return np.fromstring(dtype_value[1], sep=',', dtype=dtype_value[0])

def is_only_az_AZ(s):
    return all(c.isalpha() or c==" " for c in s)
