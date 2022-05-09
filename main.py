import streamlit as st
import pandas as pd
import numpy as np
import MeCab
import ipadic
import csv
import japanize_matplotlib
from gensim.models.keyedvectors import KeyedVectors  #学習済みWord2vecモデルを読みこむ際、使用。
from scipy import spatial
from googletrans import Translator
import io

# import s3fs
# fs = s3fs.S3FileSystem(anon=False)

st.title("翻訳ほんやく抹茶味")
st.write('日本語の文章を他言語に変換し、日本語に再変換した時に文章の意味がどれくらい変わるか判断します。')
reading_model = st.empty()
reading_model.text("現在プログラムを読み込み中ですので、お待ちください...")

CHASEN_ARGS = r' -F "%m\t%f[7]\t%f[6]\t%F-[0,1,2,3]\t%f[4]\t%f[5]\n"'
CHASEN_ARGS += r' -U "%m\t%m\t%m\t%F-[0,1,2,3]\t\t\n"'
wakati = MeCab.Tagger(ipadic.MECAB_ARGS + CHASEN_ARGS)# MeCab -Ochasen
language_df = pd.read_csv('languages.csv')

@st.cache(allow_output_mutation=True)
def load_model():
    # loaded = KeyedVectors.load('data/model', mmap='r')# load w2v model
    # loaded = KeyedVectors.load('https://streamlithonyakudata.s3.ap-northeast-1.amazonaws.com/model', mmap='r')
    # loaded = KeyedVectors.load_word2vec_format('model.bin', binary=True , unicode_errors='ignore')
    loaded = KeyedVectors.load_word2vec_format('https://streamlithonyakudata.s3.ap-northeast-1.amazonaws.com/model.bin', binary=True , unicode_errors='ignore')
    return loaded

model = load_model()
reading_model.empty()

def main():
    uploader = st.file_uploader("テキストファイルをアップロード、またはテキストボックスに文章を入力してください。", type=['txt'])
    text_box = st.text_area(label="", placeholder='テキストボックス：日本語の文章を入力してください。\n 例：坊主が屏風に上手に坊主の絵を描いた。', max_chars=1000)
    language_option = st.selectbox('どの言語に翻訳しますか？',language_df['日本語'])
    count_option = st.selectbox('何回翻訳しますか？（2回英語の場合、文章を 英語 → 日本語 → 英語 → 日本語 の順に翻訳します。）',[i for i in range(1,6)])

    button_pressed = st.button('翻訳を始める')
    if (text_box.strip() != "") and button_pressed:
        translate(text_box, language_option, count_option)
    elif uploader is not None and button_pressed:
        stringio = io.StringIO(uploader.getvalue().decode("utf-8"))
        translate(stringio.read(), language_option, count_option)
    elif button_pressed:
        st.write('<span style="color:red;">ファイルをアップロードするか、テキストボックスに文章を書いてください。</span>',unsafe_allow_html=True)


def translate(text, language, count):
    honyaku_now = st.empty()
    honyaku_now.text("翻訳中...")
    tr = Translator(service_urls=['translate.googleapis.com'])
    initial_vector = average_vec(wakati_gaki(text))
    initial_text = text
    option = language_df['abbrev'][language_df.index[language_df['日本語'] == language]].tolist()[0]

    honyaku = ""
    for i in range(count):
        text = tr.translate(text, src="ja", dest=option).text
        text = tr.translate(text, src=option, dest="ja").text
        honyaku+=language + " → " + "日本語 → "
    last_vector = average_vec(wakati_gaki(text))
    status_text = st.empty()
    similarity = (1 - spatial.distance.cosine(initial_vector, last_vector))
    less = ""
    honyaku_now.empty()
    if similarity < 0.01:
        similarity = 0.01
        less = "未満"
    progress_bar = st.progress(int(similarity*100))
    status_text.text(f'意味の類似度: {int(similarity*100)}%{less}')
       
    initial = st.text_area(label="インプット時の文章", value=initial_text, max_chars=1000, on_change=None)
    output = st.text_area(label=honyaku[:-2]+"の順に翻訳された文章", value=text, max_chars=1000, on_change=None)

    f = open('output.txt', 'w')
    f.write(text)
    download_btn = st.download_button(label="翻訳されたテキスト（txt形式）をダウンロード",data=text,file_name='output.txt')


def wakati_gaki(text):
    wakati_words = []
    node = wakati.parseToNode(text)
    while node:
        word = node.surface
        if node.feature.split(",")[0] in ['名詞','動詞','形容詞']:#ワードが特定の品詞体系に存在するか、確認する。
            if word in model and word!="*":
                wakati_words.append(word)
        node = node.next
    return wakati_words


def average_vec(wakati_words):
    average_vector = [0 for i in range(200)]
    for word in wakati_words:
        average_vector+=model.get_vector(word)
    return average_vector / len(wakati_words)

if __name__ == '__main__':
    main()
