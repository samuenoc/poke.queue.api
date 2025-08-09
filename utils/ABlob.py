import os
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
import logging
load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_SAK")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER")

logger = logging.getLogger(__name__)

class ABlob:
    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        self.container_client = self.blob_service_client.get_container_client(AZURE_STORAGE_CONTAINER)

    def generate_sas(self, id: int):
        blob_name = f"poke_report_{id}.csv"
        sas_token = generate_blob_sas(
            account_name=self.blob_service_client.account_name,
            container_name=AZURE_STORAGE_CONTAINER,
            blob_name=blob_name,
            account_key=self.blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=1)
        )
        return sas_token
    
    def delete_blob(self, id: int) -> bool:
        
        try:
            blob_name = f"poke_report_{id}.csv"
            logger.info(f"Intentando eliminar blob: {blob_name}")
            
            blob_client = self.blob_service_client.get_blob_client(
                container=AZURE_STORAGE_CONTAINER, 
                blob=blob_name
            )
            
            logger.info(f"Container: {AZURE_STORAGE_CONTAINER}")
            logger.info(f"Storage account: {self.blob_service_client.account_name}")
            
            # Verificar si el blob existe
            blob_exists = blob_client.exists()
            logger.info(f"¿Blob {blob_name} existe? {blob_exists}")
            
            if not blob_exists:
                logger.warning(f"Blob {blob_name} no existe en el contenedor")
                return False
            
            # Eliminar el blob
            logger.info(f"Eliminando blob {blob_name}...")
            delete_response = blob_client.delete_blob()
            logger.info(f"Respuesta de eliminación: {delete_response}")
            logger.info(f"Blob {blob_name} eliminado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando blob poke_report_{id}.csv: {str(e)}")
            logger.error(f"Tipo de error: {type(e).__name__}")
            raise Exception(f"Error eliminando archivo del storage: {str(e)}")