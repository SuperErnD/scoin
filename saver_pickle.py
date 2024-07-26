import pickle
from bc import Blockchain

class Saver:
    def init(self):
        pass

    def save(self, data: Blockchain):
        with open('blockchain.pickle', 'wb') as f:
            pickle.dump(data, f)

    def load(self) -> Blockchain:
        with open('blockchain.pickle', 'rb') as f:
            return pickle.load(f)