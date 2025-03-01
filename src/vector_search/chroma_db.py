import chromadb


class ChromaClient:
    def __init__(self) -> None:
        self.client = chromadb.PersistentClient("db/")

    def client_info(self):
        print(self.client)

    def collection_info(self):
        print(self.client.list_collections())

    def create_collection(self, collection_name):
        collection = self.client.get_or_create_collection(name=collection_name)
        return collection
