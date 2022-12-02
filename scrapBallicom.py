from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException 
from selenium import webdriver
from fake_useragent import UserAgent
import json
import os.path
 

class WebScraping:
	def __init__(self):
		# Setting webdriver
		options = Options()
		ua = UserAgent()
		options.binary_location = '/usr/bin/brave-browser'
		options.add_argument("--incognito")
		options.add_argument(f'user-agen={ua.random}')
		self.driver = webdriver.Chrome(options = options)
		self.domain = 'https://www.ballicom.co.uk/'
		self.main_categories = ['hardware', 'electronics', 'office-supplies', 'software', 'facilities', 'other']
		self.categories = []
		self.categories_filename = "ballicom_categories.json"
		self.products_filename = "ballicom_products.json"
		self.products_csv = "product_list.csv"


	# Start scraping
	def scrap_ballicom(self):
		if os.path.isfile("./"+self.categories_filename):
			# Read categories
			self.categories = self.read_categories_file()
			# Get the list of products for each category
			self.get_product_list()
		else:
			# Look for subcategories
			for category in self.main_categories:
				self.driver.get(self.domain + category)
				print("Scraping Ballicom " + category + "...")
				if self.check_exists('[class="product-listing category row"]'):
					self.scrap_category()
				print("--Categories extracted: " + str(len(self.categories)))
			# Write categories file
			print("All categories extracted")
			self.write_categories_to_file()
			self.get_product_list()


	# Scraping subcategories recursively
	def scrap_category(self):
		# Get category list
		ulist = self.driver.find_element(By.CSS_SELECTOR, '[class="product-listing category row"]')
		sec_categ = ulist.find_elements(By.TAG_NAME, 'a')
		sec_categ_list = list(map(lambda x: x.get_attribute("href"), sec_categ))

		# Iterate category level
		for sec_url in sec_categ_list:
			self.driver.get(sec_url)
			# If there is a category list - go to next category level
			if self.check_exists('[class="product-listing category row"]'):
				self.scrap_category()
			# If there is not other category level, add url to array and go to previous category
			else:
				self.categories.append(sec_url)
				self.driver.back()
		self.driver.back()


	# Scraping final category product list
	def get_product_list(self):
		for category in self.categories:
			print("Scraping products: "+ category)
			self.driver.get(category)
			self.driver.maximize_window()
			item_200_per_page = self.driver.find_element(By.ID, "item_per_page_200")
			item_200_per_page.click()
			end_page = False
			products_url_list = []
			while end_page == False:
				# Scrap products list
				product_list = self.driver.find_element(By.CSS_SELECTOR, '[class="product-listing"]')
				product_element_list = product_list.find_elements(By.TAG_NAME, 'a')
				products_url_list += list(map(lambda x: x.get_attribute("href"), product_element_list))
				# Check last page
				end_page = self.check_last_page()
				if end_page == False:
					pagination_element = self.driver.find_element(By.XPATH, '//div[@class="pagination"]/ul')
					pagination_elements = pagination_element.find_elements(By.XPATH, './/li/a')
					next_element = pagination_elements[len(pagination_elements)-1]
					next_element.click()
			# Get category name
			category_name = self.extract_category_name(category)
			# Scrap product
			for product_url in products_url_list:
				self.get_product(product_url, category_name)
			print("Products scraped")


	# Scraping product data
	def get_product(self, product_url, category_name):
		self.driver.close()
		self.set_driver_options()
		self.driver.get(product_url)
		# Title
		if self.check_exists('[class="products_name"]'):
			title = self.driver.find_element(By.CSS_SELECTOR,'[class="products_name"]').text
		else: 
			title = ""
		# Post name
		post_name = title.replace(" ","-").lower() 
		# Price
		if self.check_exists('[itemprop="price"]'):
			price = self.driver.find_element(By.CSS_SELECTOR,'[itemprop="price"]').text
		else: 
			price = ""
		# RRPPrice
		if self.check_exists('[class="price-line rrpprice"]'):
			rrpprice = self.driver.find_element(By.CSS_SELECTOR,'[class="price-line rrpprice"]').text
			rrpprice = rrpprice.replace("RRP: £","").replace(" inc VAT","")
		else:
			rrpprice = ""
		# Basic Specs
		if self.check_exists('[class="basic-specification tab-image"]'):
			specification_el = self.driver.find_element(By.CSS_SELECTOR,'[class="basic-specification tab-image"]')
			specifications_divs = specification_el.find_elements(By.XPATH, './/div/*')
			specifications_list = list(map(lambda x: x.get_attribute('innerHTML'), specifications_divs))
			basic_specifications = ", ".join(specifications_list)
		else:
			basic_specifications = ""
		# Full Specs
		if self.check_exists('[class="basic-specification tab-image"]'):
			full_specifications = ""
			full_specs_els = self.driver.find_elements(By.CSS_SELECTOR,'[class="basic-specification tab-image"]')
			full_specs_els.pop(0)
			for spec_el in full_specs_els:
				spec_divs = spec_el.find_elements(By.XPATH, './/div/*')
				spec_list = list(map(lambda x: x.get_attribute('innerHTML'), spec_divs))
				full_specifications += ", ".join(spec_list)
		else:
			full_specifications = ""
		# Image
		if self.check_exists('[itemprop="image"]'):
			image_div = self.driver.find_element(By.CSS_SELECTOR,'[class="swiper-slide swiper-slide-active"]')
			image = image_div.find_element(By.XPATH,'.//img')
			image = image.get_attribute('src')
		else:
			image = ""
		# Creating product dictionary data
		product_dict = {"name": title, "full_specifications": full_specifications, "basic_specifications": basic_specifications,
		"regular_price": rrpprice, "sale_price": price, "category": category_name, "image": image, "url":product_url} 
		self.write_product_to_file(product_dict)


	# Writing product to file
	def write_product_to_file(self, product_dict):
		data = []
		if os.path.isfile("./"+self.products_filename):
			pass
		else:
			# Write json file
			with open(self.products_filename, "w") as file:
				json.dump(data, file, indent=4)

		# Read file contents
		with open(self.products_filename, "r") as file:
			data = json.load(file)
			# Update json object
			data.append(product_dict)
		# Write json file
		with open(self.products_filename, "w") as file:
			json.dump(data, file, indent=4)


	# Writing categories to file
	def write_categories_to_file(self):
		print("Writing categories")
		# Write json file
		with open(self.categories_filename, "w") as file:
			json.dump(self.categories, file, indent=4)


	# Read categories file
	def read_categories_file(self):
		print("Reading categories")
		with open(self.categories_filename, "r") as file:
		    data = json.load(file)
		return data


	# Extract category name
	def extract_category_name(self, category):
		try:
			first_split = category.split("/")
			second_split = first_split[-2].split("-")
			categoriy_list = list(map(lambda x: x.capitalize(), second_split))
			category_name = " ".join(categoriy_list)
		except:
			category_name = "Uncategorized"
		return category_name


	# Checking if it is last page od product list
	def check_last_page(self):
		div_pages = self.driver.find_element(By.CSS_SELECTOR, '[class="txt-st-1 pg-txt"]')
		txt_page = div_pages.find_element(By.XPATH, './/p').text
		txt_page_split = txt_page.split(" to ")
		end_txt_page_split = txt_page_split[1].split(" (of ")
		actual = end_txt_page_split[0]
		last = end_txt_page_split[1].replace(" Products)","")
		if actual == last:
			return True
		else:
			return False

	def set_driver_options(self):
		# Setting webdriver
		options = Options()
		ua = UserAgent()
		options.binary_location = '/usr/bin/brave-browser'
		options.add_argument("--incognito")
		options.add_argument(f'user-agen={ua.random}')
		self.driver = webdriver.Chrome(options = options)

	# Checking if DOM element class exists
	def check_exists(self, class_name):
	    try:
	        self.driver.find_element(By.CSS_SELECTOR, class_name)
	    except NoSuchElementException:
	        return False
	    return True


if __name__ == "__main__":
	web_scrap = WebScraping()
	web_scrap.scrap_ballicom()
