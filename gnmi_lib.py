"""Python3 library used for interacting with network elements using gNMI.

This library used for Get and SetRequests using gNMI.
"""
import json
import re
from typing import List, Text, Iterable, Optional
import gnmi_pb2  # pip install protobuf
import gnmi_pb2_grpc
import grpc


_RE_PATH_COMPONENT = re.compile(r'''
^
(?P<pname>[^[]+)  # gNMI path name
(\[(?P<key>\w\D+)   # gNMI path key
=
(?P<value>.*)    # gNMI path value
\])?$
''', re.VERBOSE)


class Error(Exception):
  """Module-level Exception class."""


class XpathError(Error):
  """Error parsing xpath provided."""


def PathNames(xpath: Text) -> List[Text]:
  """Parses the xpath names.

  This takes an input string and converts it to a list of gNMI Path names. Those
  are later turned into a gNMI Path Class object for use in the Get/SetRequests.
  Args:
    xpath: (str) xpath formatted path.

  Returns:
    list of gNMI path names.
  """
  if not xpath or xpath == '/':  # A blank xpath was provided.
    return []
  return re.split(r'''/(?=(?:[^\[\]]|\[[^\[\]]+\])*$)''',
                  xpath.strip('/').strip('/'))  # Removes leading/trailing '/'.


def ParsePath(p_names: Iterable[Text]) -> gnmi_pb2.Path:
  """Parses a list of path names for path keys.

  Args:
    p_names: (list) of path elements, which may include keys.

  Returns:
    a gnmi_pb2.Path object representing gNMI path elements.

  Raises:
    XpathError: Unabled to parse the xpath provided.
  """
  gnmi_elems = []
  for word in p_names:
    word_search = _RE_PATH_COMPONENT.search(word)
    if not word_search:  # Invalid path specified.
      raise XpathError('xpath component parse error: %s' % word)
    if word_search.group('key') is not None:  # A path key was provided.
      tmp_key = {}
      for x in re.findall(r'\[([^]]*)\]', word):
        tmp_key[x.split('=')[0]] = x.split('=')[-1]
      gnmi_elems.append(gnmi_pb2.PathElem(name=word_search.group(
          'pname'), key=tmp_key))
    else:
      gnmi_elems.append(gnmi_pb2.PathElem(name=word, key={}))
  return gnmi_pb2.Path(elem=gnmi_elems)


def CreateCreds(
    root_cert: Optional[Text] = None) -> grpc.ssl_channel_credentials:
  """Creates credentials used in gNMI Requests.

  Args:
    root_cert: (str) Target root certificate to use in validating gRPC channel.

  Returns:
    a gRPC.ssl_channel_credentials object.
  """
  return grpc.ssl_channel_credentials(
      root_certificates=root_cert, private_key=None, certificate_chain=None)


def CreateStub(creds: grpc.ssl_channel_credentials,
               target: Text,
               port: Text,
               host_override: Optional[Text] = None) -> gnmi_pb2_grpc.gNMIStub:
  """Creates a gNMI GetRequest.

  Args:
    creds: (object) of gNMI Credentials class used to build the secure channel.
    target: (str) gNMI Target.
    port: (str) gNMI Target IP port.
    host_override: (str) Hostname being overridden for Cert check.

  Returns:
    a gnmi_pb2_grpc object representing a gNMI Stub.
  """
  if host_override:
    channel = grpc.secure_channel(target + ':' + port, creds, ((
        'grpc.ssl_target_name_override',
        host_override,
    ),))
  else:
    channel = grpc.secure_channel(target + ':' + port, creds)
  return gnmi_pb2_grpc.gNMIStub(channel)


def Get(stub: gnmi_pb2_grpc.gNMIStub, paths: gnmi_pb2.Path, username: Text,
        password: Text) -> gnmi_pb2.GetResponse:
  """Creates a gNMI GetRequest.

  Args:
    stub: (class) gNMI Stub used to build the secure channel.
    paths: gNMI Path
    username: (str) Username used when building the channel.
    password: (str) Password used when building the channel.

  Returns:
    a gnmi_pb2.GetResponse object representing a gNMI GetResponse.
  """
  if username and password:  # User/pass supplied for Authentication.
    return stub.Get(
        gnmi_pb2.GetRequest(path=[paths], encoding='JSON_IETF'),
        metadata=[('username', username), ('password', password)])
  return stub.Get(gnmi_pb2.GetRequest(path=[paths], encoding='JSON_IETF'))


def Set(stub: gnmi_pb2_grpc.gNMIStub, paths: gnmi_pb2.Path, username: Text,
        password: Text, json_value: Text,
        set_type: Text) -> gnmi_pb2.SetResponse:
  """Creates a gNMI SetRequest.

  Args:
    stub: (class) gNMI Stub used to build the secure channel.
    paths: gNMI Path.
    username: (str) Username used when building the channel.
    password: (str) Password used when building the channel.
    json_value: (str) JSON_IETF Value or file.
    set_type: (str) Type of gNMI SetRequest to build.
  Returns:
    a gnmi_pb2.SetResponse object representing a gNMI SetResponse.
  """
  if json_value:  # Specifying ONLY a path is possible for Delete.
    val = gnmi_pb2.TypedValue()
    val.json_ietf_val = json.dumps(json_value).encode('utf8')
    path_val = gnmi_pb2.Update(path=paths, val=val,)
  if set_type == 'update':
    return stub.Set(gnmi_pb2.SetRequest(update=[path_val]), metadata=[
        ('username', username), ('password', password)])
  elif set_type == 'replace':
    return stub.Set(gnmi_pb2.SetRequest(replace=[path_val]), metadata=[
        ('username', username), ('password', password)])
  elif set_type == 'delete':
    return stub.Set(gnmi_pb2.SetRequest(delete=[paths]), metadata=[
        ('username', username), ('password', password)])
