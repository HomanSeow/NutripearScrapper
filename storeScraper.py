import requests
from bs4 import BeautifulSoup
import json
from datetime import date
import regex
class grocery_scrapper:
    def __init__(self, store):
        self.store_id = 2776
        self.store = dict()
        self.store["name"] = store
        self.store["id"] = self.store_id
        self.store["link"] = "https://www.target.com"
        self.global_categories_links = []
        self.all_category_links = []
        self.final_json_list = []
        self.file_number = 0

    def gather_global_categories(self):
        """
        gather all the links to every category related to food
        """
        food_categories= "https://www.target.com/c/food-beverage/-/N-5xt1a?lnk=snav_rd_grocery"
        response = requests.get(food_categories)
        html_soup = BeautifulSoup(response.text, 'html.parser')
        category_class_name = "FilmstripItem-jx5f9b-0 ePEYNE filmstripItem"
        global_category_list = html_soup.find_all('li', class_ = category_class_name)
        for category in global_category_list:  
            category_partial_link = category.find('a').get('href')
            category_link = self.store["link"] + str(category_partial_link)
            self.global_categories_links.append(category_link)

    def gather_sub_categories(self):
        """
        each global categories have sub categories, for instance with the global category produce
        it will contain sub categories such as fruits, vegetables, etc....
        """
        for sub_categories in self.global_categories_links:
            response = requests.get(sub_categories)
            html_soup = BeautifulSoup(response.text, 'html.parser')
            class_name = "Link-sc-1khjl8b-0 ItemLink-sc-1eyz3ng-0 kdCHb dtKueh"
            sub_category_list = html_soup.find_all('a', class_ = class_name)
            for category in sub_category_list:  
                category_link = category.get('href')
                category_link = self.store["link"] + str(category_link)
                self.all_category_links.append(category_link)
    

    def __generate_products_list(self, category_id,page_number ):
        """
        generates the link to all products within sub categories
        """
        page_number = 24 * page_number
        products_info = "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v1?key=ff457966e64d5e877fdbad070f276d18ecec4a01&category={0}&channel=WEB&count=24&default_purchasability_filter=true&include_sponsored=true&offset={1}&page=%2Fc%2F{0}&platform=desktop&pricing_store_id=3233&scheduled_delivery_store_id=336&store_ids=3233%2C336%2C2151%2C250%2C2128&useragent=Mozilla%2F5.0+%28Windows+NT+10.0%3B+Win64%3B+x64%29+AppleWebKit%2F537.36+%28KHTML%2C+like+Gecko%29+Chrome%2F87.0.4280.141+Safari%2F537.36&visitor_id=0175E2BE790D04012036C52569D9CB50".format(category_id,page_number)
        return products_info

    def __next_page_available(self, products_info):  
        """
        check if there is a next page for this product section
        """
        products_json = json.loads(requests.get(products_info).text)
        if len(products_json['data']['search']['products']) == 0 or 'data' not in products_json:
            return False
        return True

    def __generate_products_json(self, products_json):
        """
        generates the jsons for each product
        """

        for i in range(len(products_json['data']['search']['products'])):
            retail_information = dict();
            product = products_json['data']['search']['products'][i]
            retail_information["product_name"] = product['item']['product_description']['title']
            retail_information["buy_link"] = product['item']['enrichment']['buy_url']
            if('dpci' in product['item']):
                retail_information["barcode/dpci"] = product['item']['dpci']
            if('price' in product):
                retail_information["price"] = product['price']['formatted_current_price']
            if('ratings_and_reviews' in product):
                rating = product['ratings_and_reviews']['statistics']['rating']
                retail_information["rating"] = rating["average"]
                retail_information["price last updated"] = str(date.today())
            product_link = retail_information["buy_link"]
            product_info = "https://redsky.target.com/v2/plp/collection/{0}?key=ff457966e64d5e877fdbad070f276d18ecec4a01&pricing_store_id={1}".format(product_link.split("-")[-1],self.store["id"])
            product_json = json.loads(requests.get(product_info).text)
            if("upc" in product_json["search_response"]["items"]["Item"][0]):
                product_upc = product_json["search_response"]["items"]["Item"][0]["upc"]
                retail_information["upc"]= product_upc
            final_product_json = self.__gather_nutrition_and_ingredients(retail_information)
            json.dumps(final_product_json,indent=4)
            self.final_json_list.append(final_product_json)

    
    def __gather_nutrition_and_ingredients(self, retail_information):
        """ 
        gather product's nutritional label and ingredients and saves it in a dictionary 
        """
        response = requests.get(retail_information["buy_link"])
        pattern = regex.compile(r'"nutrition_facts":{.*}]}].*?}')
        nutrition_information_list = pattern.findall(response.text)
        nutrition_dict = dict()
        try:
            if(len(nutrition_information_list)!= 0):
                nutrition_information_list[0] = nutrition_information_list[0]
                nutrition_ingredients_json_string = "{"+nutrition_information_list[0]+"}"
                nutrition_ingredients = json.loads(nutrition_ingredients_json_string)
                nutrition_facts = nutrition_ingredients["nutrition_facts"]
                nutrition_list = nutrition_facts["value_prepared_list"][0]
                if("ingredients" in nutrition_facts):
                    nutrition_dict["ingredients"] = nutrition_facts["ingredients"]
                if("serving_size" in nutrition_list):
                    nutrition_dict["serving_size"] = nutrition_list["serving_size"]
                if("serving_size_unit_of_measurement" in nutrition_list):
                    nutrition_dict["serving_size_unit_of_  measurement"] = nutrition_list["serving_size_unit_of_measurement"]
                if("servings_per_container" in nutrition_list):
                    nutrition_dict["servings_per_container"] = nutrition_list["servings_per_container"]
                if("warning" in nutrition_facts): 
                    nutrition_dict["warning"] = nutrition_facts["warning"]
                for nutrient in nutrition_list["nutrients"]:
                    if("name" in nutrient):
                        name = nutrient["name"]
                    else:
                        continue
                    for key in nutrient:
                        if key != "name":
                            name = name.replace(" ","_")
                            name = name.replace(".","_")
                            nutrition_dict[name+"_"+key] = nutrient[key]
                retail_information.update(nutrition_dict)
        except:  
            print(nutrition_ingredients_json_string)
        return retail_information

    def gather_products(self):
        """ 
            gathers all the products and outputs it in json file
        """
        for index, category_links in enumerate(self.all_category_links):
            page_number = 0;
            category_id = category_links.split('-')[-1] 
            while True:
                products_info = self.__generate_products_list(category_id, page_number)
                print(products_info)
                products_json = json.loads(requests.get(products_info).text)
                self.__generate_products_json(products_json)
                if(not self.__next_page_available(products_info)):
                    break;
                else:
                    page_number+=1

            self.__export_to("product_file_", self.file_number)
            self.file_number+=1
            self.final_json_list = []
           
        
    def __export_to(self, filename, file_number):
        output = filename + str(file_number) + ".json"
        with open(output,"w") as fp:
            json.dump(self.final_json_list,fp,indent=4)


if __name__ == "__main__":
    target = grocery_scrapper("target")
    target.gather_global_categories()
    target.gather_sub_categories()
    target.gather_products()
