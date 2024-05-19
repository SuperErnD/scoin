import pickle

class Saver:
    def init(self):
        pass

    def save(self, data):
        with open('blockchain.pickle', 'wb') as f:
            pickle.dump(data, f)

    def load(self):
        with open('blockchain.pickle', 'rb') as f:
            return pickle.load(f)