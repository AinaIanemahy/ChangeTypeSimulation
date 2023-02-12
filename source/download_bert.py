from transformers import BertTokenizer, BertModel
import sys

path = sys.argv[1]

tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained("bert-base-uncased")
tokenizer.save_pretrained(path)
model.save_pretrained(path)