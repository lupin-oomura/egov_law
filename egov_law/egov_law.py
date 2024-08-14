import requests, json
from lxml import etree
import os

class egov_law :

    save_folder = None

    def __init__(self) :
        pass


    def set_save_folder(self, fld:str) :
        self.save_folder = fld
        if not os.path.exists(fld):
            os.mkdir(fld)

    def get_law_dict(self, category: int = 1, f_save:bool=False):
        # category 1:全法令, 2:憲法・法律, 3:政令・勅令, 4:府省令

        if self.save_folder == None and f_save == True :
            print("set [save folder] first !!")
            return None

        url = f"https://elaws.e-gov.go.jp/api/1/lawlists/{category}"
        r = requests.get(url)
        # XMLデータの解析
        root = etree.fromstring(r.content)

        # 辞書{名称: 法令番号}の作成
        names = [e.text for e in root.xpath(".//LawName")]
        ids = [e.text for e in root.xpath(".//LawId")]
        numbers = [e.text for e in root.xpath(".//LawNo")]
        dic = {id: {name: num} for (id, name, num) in zip(ids, names, numbers)}

        if f_save == True :
            fn = f"law_list.json"
            with open(os.path.join(self.save_folder, fn), "w", encoding='utf-8') as f:
                json.dump(dic, f, ensure_ascii=False, indent=4)

        return dic




    def get_law_contents(self, law_id:str, f_save:bool=False) -> dict :

        if self.save_folder == None and f_save == True :
            print("set [save folder] first !!")
            return None
        
        url = f"https://elaws.e-gov.go.jp/api/1/lawdata/{law_id}"
        response = requests.get(url)
        doc = etree.fromstring(response.content)


        # 原文の全てのテキストを抽出し、加工する
        l_raw_contents = [e.text.strip() for e in doc.iter() if e.text]
        l_raw_contents = [t.replace('\u3000', '　') for t in l_raw_contents if t]
        l_raw_contents = l_raw_contents[2:] #最初の2行はおそらくメタ情報
        raw_contents = '\n'.join(l_raw_contents)


        # LawNum要素を取得する
        law_num_el = doc.xpath(".//LawNum")
        print(law_num_el[1].text if law_num_el[1].text else "[法律番号]要素が見つかりませんでした")

        # LawTitle要素を取得する
        law_title_el = doc.xpath(".//LawBody/LawTitle")
        print(law_title_el[0].text if law_title_el[0].text else "[法令名]要素が見つかりませんでした")


        # 目次データを取得し、出力する
        toc_el = doc.xpath(".//TOC")
        l_toc = []
        if toc_el:
            print("\n目次:")
            toc_chapters = toc_el[0].xpath(".//TOCChapter")
            for chapter in toc_chapters:
                chapter_title = chapter.xpath(".//ChapterTitle")[0].text.strip()
                article_range = chapter.xpath(".//ArticleRange")
                if article_range :
                    article_range = chapter.xpath(".//ArticleRange")[0].text.strip()
                else :
                    article_range = ""
                print(f"{chapter_title} {article_range}")
                l_toc.append( {"title": chapter_title, "range": article_range} )
        else:
            print("目次要素が見つかりませんでした")



        #本則と附則を足し合わせて処理
        main_provision_el = doc.xpath(".//LawBody/MainProvision")
        supp_provision_el = doc.xpath(".//LawBody/SupplProvision")
        l_provision_el = main_provision_el + supp_provision_el

        l_provision = []
        for provision_el in l_provision_el :
            # 本則 / 附則
            suppl_label_el = provision_el.xpath(".//SupplProvisionLabel")
            suppl_label = suppl_label_el[0].text.replace("　","") if suppl_label_el else "本則"
            # 改訂履歴NO
            amend_law_num = provision_el.get("AmendLawNum")
            amend_law_num = amend_law_num if amend_law_num else ""

            dic_provision = {}
            dic_provision['suppl_label'] = suppl_label
            dic_provision['amend_law_num'] = amend_law_num
            
            mp_article_el_list = provision_el.xpath(".//Article")
            l_jou = []
            for article_el in mp_article_el_list:
                # ArticleCaptionの取得と出力
                article_caption = ""
                article_caption_el = article_el.xpath(".//ArticleCaption")
                if article_caption_el:
                    # print(f"　{article_caption_el[0].text.strip()}")
                    article_caption = article_caption_el[0].text.strip()
                else:
                    # print(f"　{article_caption}")
                    pass

                # ArticleTitleの取得と出力
                article_title = article_el.xpath(".//ArticleTitle")[0].text.strip()
                jou = {"caption": article_caption, "title": article_title, "contents": []}
                
                # Paragraphの処理
                for pi, paragraph_el in enumerate(article_el.xpath(".//Paragraph")):
                    paragraph_num_el = paragraph_el.xpath(".//ParagraphNum")[0]
                    paragraph_sentence_el = paragraph_el.xpath(".//ParagraphSentence")[0]
                    paragraph_sentence = ''.join(paragraph_sentence_el.xpath(".//text()")).strip()
                    paragraph_sentence = paragraph_sentence.replace(' ', '').replace('\n', ' ')
                    if paragraph_num_el.text:
                        no = paragraph_num_el.text.strip()
                        # print(f"{no}　{paragraph_sentence}")
                    else:
                        no = "１"
                        # print(f"{article_title}　{paragraph_sentence}")

                    kou = {"no": no, "sentence": paragraph_sentence}

                    # Itemの処理
                    l_gou = []
                    for item_el in paragraph_el.xpath(".//Item"):
                        item_title_el    = item_el.xpath(".//ItemTitle")[0]
                        item_sentence_el = item_el.xpath(".//ItemSentence")[0]
                        item_sentence    = ''.join(item_sentence_el.xpath(".//text()")).strip()
                        item_sentence    = item_sentence.replace(' ', '').replace('\n', ' ')


                        # if item_title_el and item_sentence_el:
                        #     print(f"　{item_title_el.text.strip()}　{item_sentence}")
                        gou = {"no": item_title_el.text.strip(), "sentence": item_sentence}
                        l_gou.append(gou)
                    
                    kou["gou"] = l_gou
                    jou["contents"].append(kou)

                l_jou.append(jou)

            dic_provision['jou'] = l_jou
            l_provision.append(dic_provision)
            del dic_provision



        # 原文の全てのテキストを抽出し、加工する
        l_raw_contents = [e.text.strip() for e in doc.iter() if e.text]
        l_raw_contents = [t.replace('\u3000', '　') for t in l_raw_contents if t]
        l_raw_contents = l_raw_contents[2:] #最初の2行はおそらくメタ情
        raw_contents = '\n'.join(l_raw_contents)

        dic = {
            "law_id": law_id,
            "law_num": law_num_el[0].text,
            "law_title": law_title_el[0].text,
            "toc": l_toc,
            "contents": l_provision,
            "raw_contents": raw_contents
        }

        if f_save == True :
            fn = f"law_{law_id}.json"
            with open(os.path.join(self.save_folder, fn), "w", encoding='utf-8') as f:
                json.dump(dic, f, ensure_ascii=False, indent=4)

        return dic

if __name__ == '__main__' :
    egovlow = egov_low()
    egovlow.set_save_folder("data_20240815")

    dic_laws = egovlow.get_law_dict(category=2, f_save=True) # category 1:全法令, 2:憲法・法律, 3:政令・勅令, 4:府省令

    # chk_id = '412AC0000000061' #消費者契約法
    chk_id = '345AC0000000139'
    f_pass = True
    for law_id, itm in dic_laws.items() :
        if law_id == chk_id :
            f_pass = False
        if f_pass == False :
            print(f"---{law_id}({itm})---------------")
            dic_law_data = egovlow.get_law_contents(law_id, True)

