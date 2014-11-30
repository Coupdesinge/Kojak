import pickle
import re
import glob
import pymongo
from pymongo import MongoClient
import numpy as np
from decimal import *
getcontext().prec = 5
import random
from functools import partial


class ConnecttoDb(object):

		def connect_to_db(self, ip, name, pw):
			global db
			c = MongoClient(ip)
			if c.yelp.authenticate(name, pw) == True:
					db = c.debates
					print 'connected!'
			
			return db


class Accommodation(object):

		category_list = ['article', 'certain', 'conj', 'discrep', 'excl', 'incl', 'ipron', 'negate', 'preps', 'quant', 'tentat', 'i', 'we', 'you', 'auxverb', 'adverb']

		def get_acc(self, feat):
				m1 = len([m for m in feat if m[0] + m[1] == 2])
				m2 = len([m for m in feat if m[0] == 1])
				m3 = len([m for m in feat if m[1] == 1])
				m4 = len(feat)
				
				ACC = float(Decimal(m1)/Decimal(m2) - Decimal(m3)/Decimal(m4))
				
				return ACC

		def make_convo(self, ls):
				convo = []
				i = 0
				while i < len(ls)-1:
						convo.append([ls[i], ls[i+1]])
						i += 2

				return convo

		def get_average_accommodation(self, debatelist):
				'''debatelist is a list of featuredicts for each speaker, as created in make_random_model'''
				category_list = ['article', 'certain', 'conj', 'discrep', 'excl', 'incl', 'ipron', 'negate', 'preps', 'quant', 'tentat', 'i', 'we', 'you', 'auxverb', 'adverb']

				avg_list = []
				for c in category_list:
						lst = []
						for l in debatelist:
								lst.append(l[c])
						avg_list.append(self.get_acc(self.make_convo(lst)))

				return np.mean(avg_list)
				

		def get_feature_acc(self, debatelist, feature):
				'''test a single feature from category list
				category_list = ['article', 'certain', 'conj', 'discrep', 'excl', 'incl', 'ipron', 'negate', 'preps', 'quant', 'tentat', 'i', 'we', 'you', 'auxverb', 'adverb']
				'''

				lst = []
				for l in debatelist:
						lst.append(l[feature])
				
				return self.get_acc(self.make_convo(lst))

class DebateModel(ConnecttoDb, Accommodation):

		def create_speaker_pools(self, speaker_name, debatelist):
				'''return a feature list of all of a speaker's statements'''
				pool = []
				for d in debatelist:
						for u in db[d].find():
								if u['speaker'] == speaker_name:
										pool.append(u['features'])

				return pool

		def get_debate_scaffolding(self, debate_name):
				'''takes a debate and returns an ordered list of speaker names'''
				d_structure = []
				for u in db[debate_name].find().sort('_id', pymongo.ASCENDING):
						d_structure.append(u['speaker'])
				return d_structure


		def get_acc_value(self, debate_name, feature='ALL', order='AtoB'):
			 	
				debate = self.get_debate_scaffolding(debate_name)
				s_structure = []

				for u in db[debate_name].find().sort('_id', pymongo.ASCENDING):
						s_structure.append(u['features'])
				
				if order == 'AtoB':
						s_structure = s_structure
						debate = debate
				elif order == 'BtoA':
						s_structure = s_structure[1:]
						debate = debate[1:]

				print 'speakerA:', debate[0]
				print 'speakerB:', debate[1]
				
				if feature == 'ALL':
						acc = self.get_average_accommodation(s_structure)
				else:
						acc = self.get_feature_acc(s_structure, feature)
						
				return acc

		def get_speaker_pools(self, debate_name, debatelist):
				debate = self.get_debate_scaffolding(debate_name)
				speakerlist = list(set(debate))
				
				pooldict = {}
				for speaker in speakerlist:
						pool = self.create_speaker_pools(speaker, debatelist)
						pooldict[speaker] = pool
					

				return pooldict

		def get_acc_for_random(self, debate_name, debatelist, feature='ALL', order='AtoB'):
				
				model_list = []

				debate = self.get_debate_scaffolding(debate_name)

				if order == 'AtoB':
						debate = debate
						
				elif order == 'BtoA':
						debate = debate[1:]
				
				#print 'speakerA:', debate[0]
				#print 'speakerB:', debate[1]

				pooldict = self.get_speaker_pools(debate_name, debatelist)	

				if feature == 'ALL':
					i = 0
					while i < 1000:
						rand_structure = [random.choice(pooldict[speaker]) for speaker in debate]
						model_list.append(self.get_average_accommodation(rand_structure))

						i += 1
				else:

					i = 0
					while i < 1000:
						rand_structure = [random.choice(pooldict[speaker]) for speaker in debate]
						model_list.append(self.get_feature_acc(rand_structure, feature))
						i += 1
				
				return model_list

		def get_binary_strings(self, debate_name, feature='All'):
			'''take a debate string and feature and order return the binary string'''
			category_list = ['article', 'certain', 'conj', 'discrep', 'excl', 'incl', 'ipron', 'negate', 'preps', 'quant', 'tentat', 'i', 'we', 'you', 'auxverb', 'adverb']

			debate = self.get_debate_scaffolding(debate_name)
			s_structure = []
			
			for u in db[debate_name].find().sort('_id', pymongo.ASCENDING):
					s_structure.append(u['features'])
			
			lst = []
			for l in s_structure:
					lst.append(l[feature])

			#if feature == 'All':
			#		avg_list = []
			#		for c in category_list:
			#				lst = []
			#				for l in s_structure:
			#						lst.append(l[c])
							   		
									 
			#				return np.mean(avg_list)

			print 'speakerA:', debate[0]
			print 'speakerB:', debate[1]

			return lst

class Significance(object):

		def within_extreme_two_tail(null_value, observed_value, null_mean):
				if observed_value < null_mean:
						m_observed_value = observed_value
						observed_value = null_mean + (null_mean - observed_value)
				else:
						m_observed_value = observed_value - 2*(observed_value - null_mean)
			
				return not (observed_value > null_value > m_observed_value)

		def within_extreme_one_tail(null_value, observed_value, null_mean):
				if observed_value < null_mean:
						observed_value = null_mean + (null_mean - observed_value)
				return not (observed_value > null_value)

		def get_p_value(null_values_list, observed_value, test='two_tailed'):
				null_mean = np.mean(null_values_list)
				if test == 'one_tailed':
						comparison_func = within_extreme_one_tail
				elif test == 'two_tailed':
						comparison_func = within_extreme_two_tail

				def is_it_significant(null_value):
						return partial(comparison_func, observed_value=observed_value, null_mean = null_mean)(null_value)

				p_value = map(is_it_significant, null_values_list).count(True) / float(len(null_values_list))

				return p_value





