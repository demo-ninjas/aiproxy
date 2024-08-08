from typing import Annotated
import json
import aiproxy.data as data

def filter_array(
        array:Annotated[list, "The list of items to filter - you must provide this method"],
        field:Annotated[str, "The field within each item to match against. If the field is list, the function will match if any item in the list is a match."] = None,
        value:Annotated[str, "The match value to match against the field."] = None,
        partial:Annotated[bool, "If true, the function will return items that contain the value within the field"] = True,
        negate:Annotated[bool, "If true, the function will return items that do not match the value"] = False,
        count:Annotated[int, "The maximum number of relevant results to return. Set to 0 to return all results"] = 0,
        context:'data.ChatContext' = None
    ) -> list:
    """
    Filter a list of items by a field value
    """
    if field is None or value is None: 
        if count > 0: 
            ## Return a random selection of items upto the count
            import random
            return random.sample(array, min(count, len(array)))
        else:
            return array
    
    if array is None: return []
    
    matches = []
    non_matches = []
    for item in array:
        if type(item) is str:
            item = { field: item}
        if type(item) in [int, float]:
            item = { field: str(item)}
        elif type(item) is not dict:
            item = item.__dict__

        field_val = item.get(field, None)
        if field_val is None: 
            non_matches.append(item)
        else: 
            if isinstance(field_val, list):
                if partial:
                    if any([value in val for val in field_val]):
                        matches.append(item)
                    else: 
                        non_matches.append(item)
                else: 
                    if any([value == val for val in field_val]):
                        matches.append(item)
                    else: 
                        non_matches.append(item)
            elif isinstance(field_val, str):
                if partial: 
                    if value in field_val:
                        matches.append(item)
                    else: 
                        non_matches.append(item)
                else:
                    if value == field_val:
                        matches.append(item)
                    else: 
                        non_matches.append(item)
            else:
                str_val = str(field_val)
                if partial: 
                    if value in str_val:
                        matches.append(item)
                    else: 
                        non_matches.append(item)
                else:
                    if value == str_val:
                        matches.append(item)
                    else: 
                        non_matches.append(item)
    
    if negate:
        return non_matches[:count]
    else:
        return matches[:count]

def set_obj_field(
        obj:Annotated[any, "The object to set the value of the field on"],
        field:Annotated[str, "A string describing which  field to set the value of. This could be a field name, a list index (using square brackets - eg. '[0]' extracts the first item in a list), or a combination using dot notation (eg. 'records[0].name' will return the name of the first item in a list of records)"],
        value:Annotated[any, "The value to set the field to"],
    ) -> any:
    """
    Sets the value of the specified field within the given object
    """
    return _inner_object_update(obj=obj, field=field, value=value)


def get_obj_field(
        obj:Annotated[any, "The object to extract from"],
        field:Annotated[str, "A string describing the part of the object to extract. This could be a field name, a list index (using square brackets - eg. '[0]' extracts the first item in a list), or a combination using dot notation (eg. 'records[0].name' will return the name of the first item in a list of records)"],
    ) -> any:
    """
    Extract a part of an object as described by the field argument
    """
    return _inner_object_update(obj=obj, field=field)


def _inner_object_update(obj:any, field:str, value:any = None) -> any:
    if obj is None: return None
    if field is None: return obj

    original_object_ref = obj
    object_was_json_string = False
    if type(obj) is str:
        try: 
            obj = json.loads(obj)
            object_was_json_string = True
        except: 
            obj = { field: obj}
    elif type(obj) is not dict and type(obj) is not list:
        try:
            obj = obj.__dict__
        except: 
            pass # and hope for the best

    if field.startswith('.'): field = field[1:]
    if field.startswith('['): 
        bkt_idx = field.index(']')
        idx = field[1:bkt_idx]
        field = field[bkt_idx + 1:]
        if type(obj) is list:
            if idx.isdigit():
                idx = int(idx)
                obj = obj[idx] if idx < len(obj) else None
            elif ':' in idx:
                start, end = idx.split(':')
                start = int(start) if start else None
                end = int(end) if end else None
                obj = obj[start:end]
        ## If it's not a list, then we simply ignore this index reference ;p

    if value is None and (field is None or field == ''): 
        return obj
    
    fields = field.split('.')
    for field_name, i in zip(fields, range(len(fields))):
        is_last_field = i == len(fields) - 1
        if is_last_field and value is not None:
            if type(obj) is list: 
                ## Set field on each item in the list
                for item in obj:
                    if len(field_name) > 0: 
                        item[field_name] = value
                    else: 
                        item = value
            elif len(field_name) > 0: 
                obj[field_name] = value
            else: 
                obj = value
            if object_was_json_string:
                return json.dumps(original_object_ref)
            return original_object_ref

        list_index = None
        if '[' in field_name: 
            ## Extract the list index
            index_start = field_name.index('[')
            index_end = field_name.index(']')
            list_index = field_name[index_start + 1 : index_end]
            field_name = field_name[:index_start]

        if type(obj) is list: 
            ## Build an array of the field for each item in the list
            obj = [item.get(field_name, None) for item in obj]
        else:
            if type(obj) is str:
                try: 
                    obj = json.loads(obj)
                except: 
                    return None
            if obj is None: return None
            obj = obj.get(field_name, None)
        
        if obj is None: return None
        if list_index is not None: 
            if type(list_index) is str:
                if list_index.isdigit():
                    list_index = int(list_index)
                    if value == '-':
                        ## Remove the item from the list
                        obj.pop(list_index)
                    else:
                        obj = obj[list_index]
                elif ':' in list_index:
                    ## Extract the slice
                    start, end = list_index.split(':')
                    start = int(start) if start else None
                    end = int(end) if end else None
                    obj = obj[start:end]
                elif list_index == "*":
                    ## Return all items in the list
                    obj = obj
                elif list_index == "+":
                    ## Add the value to the list
                    obj.append(value)
            else: 
                if value == '-':
                    ## Remove the item from the list
                    obj.pop(list_index)
                else: 
                    obj = obj[list_index]

        if obj is None: return None
    return obj
    
def obj_to_json(
        obj:Annotated[any, "The object to convert to a json string"]
    ) -> str:
    """
    Convert an object to a json string
    """

    ## If object has method .to_dict(), then use it to generate the dictionary
    if hasattr(obj, 'to_api_response'):
        obj = obj.to_api_response()
    elif hasattr(obj, 'to_dict'):
        obj = obj.to_dict()
    elif hasattr(obj, 'to_json'):
        obj = obj.to_json()
        if type(obj) is str:
            return obj
    
    return json.dumps(obj, default=lambda o: o.__dict__)

def json_to_obj(
        json_str:Annotated[str, "The json string to convert to an object"]
) -> any: 
    """
    Convert a json string to an object, if possible, otherwise return None
    """
    try: 
        return json.loads(json_str)
    except:
        return None


def random_choice(
    array:Annotated[list, "The list of items to randomly choose a single item from"], 
):
    import random
    return random.choice(array)

def merge_lists(
    list1:Annotated[list, "First list."],
    list2:Annotated[list, "Second list to append to append to the end of the first list."], 
):
    result = []
    result.extend(list1)
    result.extend(list2)
    return result

def get_dict_val(key:Annotated[str, "The name of the key to retrieve the value of."], obj:dict = None) -> str:
        if obj is None: return ""

        if type(obj) is str:
            try: 
                obj = json.loads(obj)
            except: 
                return ""
        elif type(obj) is list: 
            return ",".join([ get_dict_val(key, item) for item in obj])


        val = obj.get(key, "")

        ## if the val is not found, look and see if there is a partial match (this can be commonly an issue with the AI Model calling this)
        if val == "":
            lower_key = key.lower()
            for k in obj.keys():
                if lower_key in str(k).lower():
                    val = obj.get(k, "")
                    break

        if val is None: return ""
        if type(val) in [str,int,float,bool]: return val
        if type(val) is list: 
            return ",".join([ str(item) if type(item) in [str,int,float,bool] else obj_to_json(item) for item in val])
        return obj_to_json(val)

def register_functions():
    from .function_registry import GLOBAL_FUNCTIONS_REGISTRY
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("filter_list", "Returns a filtered list of items from an array (list) of items (provided as arg 'array'). To filter the list provide the name of the 'field' (using arg 'field') to match the value your looking for. You specify the value using the 'value' arg. You can do a partial match by setting the 'partial' arg to True, otherwise setting it to False will do an exact match. You can set 'negate' to True to return all items that don't match. You can set 'count' to limit the number of results to return (you can also not specify a 'field' and 'value' and only specify count to return a random selection of items from the array upto the count size)", filter_array)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("get_obj_field", "Extract a part of an object as described by the field argument. Eg. You could extract the ingredients of the first recipe from the result of the 'search-recipes' function by setting the 'field' function argument to: 'results[0].ingredients'", get_obj_field)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("set_obj_field", "Sets the value of the specified field within the given object. Eg. You could set the name of the first record in a list of records by setting the 'field' function argument to: 'records[0].name' and the 'value' argument to the new name", set_obj_field)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("obj_to_json", "Convert an object to a json string", obj_to_json)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("json_to_obj", "Convert a json string to an object, if possible, otherwise return None", json_to_obj)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("random_choice", "Randomly choose an item from a list of items", random_choice)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("merge_lists", "Concatenate two lists together into a single list.", merge_lists)
    GLOBAL_FUNCTIONS_REGISTRY.register_base_function("get_dict_val", "Get the value of a key from a dictionary. If the value is an object or dictionary, the object will be returned as a JSON string", get_dict_val)