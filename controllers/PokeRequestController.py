import json 
import logging

from fastapi import HTTPException
from models.PokeRequest import PokemonRequest
from utils.database import execute_query_json
from utils.AQueue import AQueue
from utils.ABlob import ABlob
# configurar el logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def select_pokemon_request( id: int ):
    try:
        query = "select * from pokequeue.requests where id = ?"
        params = (id,)
        result = await execute_query_json( query , params )
        result_dict = json.loads(result)
        return result_dict
    except Exception as e:
        logger.error( f"Error selecting report request {e}" )
        raise HTTPException( status_code=500 , detail="Internal Server Error" )


async def update_pokemon_request( pokemon_request: PokemonRequest) -> dict:
    try:
        query = " exec pokequeue.update_poke_request ?, ?, ? "
        if not pokemon_request.url:
            pokemon_request.url = "";

        params = ( pokemon_request.id, pokemon_request.status, pokemon_request.url  )
        result = await execute_query_json( query , params, True )
        result_dict = json.loads(result)
        return result_dict
    except Exception as e:
        logger.error( f"Error updating report request {e}" )
        raise HTTPException( status_code=500 , detail="Internal Server Error" )
    

async def insert_pokemon_request( pokemon_request: PokemonRequest) -> dict:
    try:
        # Modificado para incluir sample_size
        query = " exec pokequeue.create_poke_request ?, ? "
        params = ( pokemon_request.pokemon_type, pokemon_request.sample_size )
        result = await execute_query_json( query , params, True )
        result_dict = json.loads(result)

        await AQueue().insert_message_on_queue( result )

        return result_dict
    except Exception as e:
        logger.error( f"Error inserting report request {e}" )
        raise HTTPException( status_code=500 , detail="Internal Server Error" )
    
async def delete_pokemon_request(id: int) -> dict:
    """
    Elimina una solicitud de reporte y su archivo CSV correspondiente
    
    Args:
        id (int): ID del reporte a eliminar
        
    Returns:
        dict: Resultado de la operación
        
    Raises:
        HTTPException: Si ocurre un error durante la eliminación
    """
    blob = ABlob()
    
    try:
        # Ejecutar stored procedure para eliminar el registro
        query = "exec pokequeue.delete_poke_request ?"
        params = (id,)
        result = await execute_query_json(query, params, True)
        result_dict = json.loads(result)
        
        # DEBUG: Log para ver qué está devolviendo el stored procedure
        logger.info(f"Stored procedure result for ID {id}: {result_dict}")
        logger.info(f"Result length: {len(result_dict)}")
        
        # El nuevo stored procedure devuelve un solo registro con toda la info
        if len(result_dict) == 0:
            logger.error(f"No result returned from stored procedure for ID {id}")
            raise HTTPException(
                status_code=500, 
                detail="Unexpected error during deletion"
            )
        
        result_record = result_dict[0]
        
        # Verificar el resultado
        if result_record.get('result') == -1:
            logger.warning(f"Request {id} not found in database")
            raise HTTPException(
                status_code=404, 
                detail=f"Report request with ID {id} not found"
            )
        elif result_record.get('result') == 1:  # Cambiar de '1' a 1
            # Eliminación exitosa
            logger.info(f"Database record for request {id} deleted successfully")
            
            # Crear objeto con la información del registro eliminado
            deleted_request = {
                'id': result_record['id'],
                'type': result_record['type'],
                'url': result_record['url'],
                'status': result_record['status']
            }
        else:
            # Error en la eliminación
            logger.error(f"Failed to delete request {id} from database")
            raise HTTPException(
                status_code=500,
                detail="Failed to delete record from database"
            )
        
        # Si llegamos aquí, el registro se eliminó exitosamente de la BD
        # Intentar eliminar el archivo del blob storage
        try:
            blob_deleted = blob.delete_blob(id)  # Quitar await
            
            if blob_deleted:
                logger.info(f"Blob and database record for request {id} deleted successfully")
                return {
                    "message": f"Report request {id} and associated file deleted successfully",
                    "deleted_request": deleted_request,
                    "blob_deleted": True
                }
            else:
                logger.warning(f"Database record deleted but blob file not found for request {id}")
                return {
                    "message": f"Report request {id} deleted successfully. Associated file was not found in storage.",
                    "deleted_request": deleted_request,
                    "blob_deleted": False
                }
                
        except Exception as blob_error:
            logger.error(f"Database record deleted but error deleting blob for request {id}: {str(blob_error)}")
            # La base de datos ya se modificó, pero falló el blob
            return {
                "message": f"Report request {id} deleted from database, but error deleting file from storage",
                "deleted_request": deleted_request,
                "blob_error": str(blob_error),
                "blob_deleted": False
            }
            
    except HTTPException:
        # Re-lanzar HTTPExceptions (como 404)
        raise
    except Exception as e:
        logger.error(f"Error deleting report request {id}: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Internal Server Error during deletion"
        )


    

async def get_all_request() -> dict:
    query = """
        select 
            r.id as ReportId
            , s.description as Status
            , r.type as PokemonType
            , r.url 
            , r.created 
            , r.updated
            , r.SampleSize  -- Incluir el nuevo campo
        from pokequeue.requests r 
        inner join pokequeue.status s 
        on r.id_status = s.id 
    """
    result = await execute_query_json( query  )
    result_dict = json.loads(result)
    blob = ABlob()
    for record in result_dict:
        id = record['ReportId']
        record['url'] = f"{record['url']}?{blob.generate_sas(id)}"
    return result_dict