"""Chido framework used for continuous integration testing.

See README for further details.
"""
import json
import socket
from absl import flags  # pip install absl-py
from absl import logging  # pip install absl-py
import chido_secrets
import grpc  # pip install grpcio
from retry import retry  # pip install retry
import pyangbind.lib.pybindJSON as pybindJSON   # pip install pyangbind
from pyangbind.lib.serialise import pybindJSONDecoder  # pip install pyangbind
import constants
import gnmi_lib

# Binding imports
from bindings.v0_2_0 import binding as v020binding
from bindings.arista import access_points as arista_aps
from bindings.ap_manager import ap_manager

_HOST_PATH = '/access-points/access-point[hostname=%s]/'
_RESPONSE = 'GNMI RESPONSE:\n%s'
_SET_UPDATE = 'update'
_MIST_GCP = 'openconfig.gc1.mist.com'
_SUPPORTED_CONTAINERS = ('radios', 'ssids', 'dot11r', 'band-steering', 'wmm',
                         'ssh', 'provision-aps', 'joined-aps', 'bssids')

FLAGS = flags.FLAGS

flags.DEFINE_string('default_ssid', '', 'The SSID to use when creating a blank '
                    'container')
# logging.set_verbosity(logging.INFO)  # uncomment to get more verbose logging.


class Error(Exception):
  """Module-level Exception class."""


class UnsupportedVendorError(Error):
  """If vendor is not supported by framework."""


class GetKeyError(Error):
  """If unable to get key from local secrets."""


class UnsupportedContainerError(Error):
  """If container given is not supported."""


class ConfigError(Error):
  """If the config leaf does not match sent configuration."""


class StateMismatchError(Error):
  """If state value does not match configured value."""


_ACCEPTABLE_ERRORS = (StateMismatchError, grpc.RpcError)
_ACCEPTABLE_ERRORS2 = (StateMismatchError, ConfigError, grpc.RpcError)


def GetPath(ap, xpath):
  """Performs Get request and display response.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    xpath: (str) the OpenConfig path to get.

  Raises:
    UnsupportedVendorError: If an AP is an unsupported vendor.
  Returns:
    gnmi_pb2.GetResponse object representing a gNMI GetResponse.
  """
  ap.targetport = constants.GNMI_TARGETPORTS[ap.vendor]
  username, password = _GetUserPass(ap.vendor)

  path = gnmi_lib.ParsePath(gnmi_lib.PathNames((xpath)))

  if ap.vendor == 'arista':
    creds = gnmi_lib.CreateCreds(constants.ARISTA_CA_CERT)
    ap.stub = gnmi_lib.CreateStub(
        creds, ap.targetip, ap.targetport, 'openconfig.mojonetworks.com')
  elif ap.vendor == 'aruba':
    creds = gnmi_lib.CreateCreds(constants.ARUBA_CA_CERT)
    ap.stub = gnmi_lib.CreateStub(
        creds, ap.targetip, ap.targetport, 'OpenConfig.arubanetworks.com')
  elif ap.vendor == 'mist':
    creds = gnmi_lib.CreateCreds()
    ap.stub = gnmi_lib.CreateStub(
        creds, _MIST_GCP, ap.targetport, _MIST_GCP)
  else:
    raise UnsupportedVendorError(
        'Unsupported vendor for AP %s, vendor: %s' % (ap.ap_name, ap.vendor))

  return gnmi_lib.Get(ap.stub, path, username, password)


def SetConfig(ap, json_path='', xpath='', json_str=''):
  """Performs Set request and display response.

  If no xpath is provided _HOST_PATH is used.  Either json_path or json_str must
  be provided as the source of configuration.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    json_path: (str) full path to JSON file.
    xpath: (str) Explicit OpenConfig tree xpath.
    json_str: (str) A valid json string.

  Returns:
    ap.gnmi_set_status: (bool) whether the gNMI SET operation passed or failed.
  """
  if json_str:
    json_data = json_str
  elif json_path:
    with open(json_path, 'rt') as data_file:
      json_data = data_file.read()
  else:
    raise ValueError('No valid path or json string provided to set config')

  payload = json.loads(json_data)
  username, password = _GetUserPass(ap.vendor)

  if xpath:
    paths = gnmi_lib.ParsePath(gnmi_lib.PathNames(xpath))
  else:
    paths = gnmi_lib.ParsePath(gnmi_lib.PathNames((_HOST_PATH % ap.ap_name)))

  if ap.vendor == 'arista':
    creds = gnmi_lib.CreateCreds(constants.ARISTA_CA_CERT)
    ap.stub = gnmi_lib.CreateStub(creds, ap.targetip, ap.targetport,
                                  'openconfig.mojonetworks.com')
  elif ap.vendor == 'aruba':
    creds = gnmi_lib.CreateCreds(constants.ARUBA_CA_CERT)
    ap.stub = gnmi_lib.CreateStub(creds, ap.targetip, ap.targetport,
                                  'OpenConfig.arubanetworks.com')
  elif ap.vendor == 'mist':
    creds = gnmi_lib.CreateCreds()
    ap.stub = gnmi_lib.CreateStub(creds, _MIST_GCP,
                                  constants.GNMI_TARGETPORTS['mist'], _MIST_GCP)

  config_response = gnmi_lib.Set(ap.stub, paths, username, password,
                                 payload, _SET_UPDATE)
  logging.info(_RESPONSE, config_response)
  ap.gnmi_set_status = True

  return ap.gnmi_set_status


def _GetContainer(ap, container):
  """Returns an OC Object (YANGBaseClass) given a container name.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    container: (str) a supported container within the model.
  Returns:
    OC Object (YANGBaseClass) matching the container name.
  Raises:
    UnsupportedContainerError: If container is not supported.
  """
  if container not in _SUPPORTED_CONTAINERS:
    raise UnsupportedContainerError('Container "%s" is not supported'
                                    % container)
  default_ssid = 'ChidoTestGuest'
  if ap.vendor == 'arista':
    configs = arista_aps.openconfig_access_points()
  else:
    configs = v020binding.openconfig_access_points()
  config_ap = configs.access_points.access_point.add(ap.ap_name)

  if container == 'radios':
    if ap.vendor == 'arista':
      return config_ap.radios.radio.add(id=0, operating_frequency='FREQ_5GHZ')
    return config_ap.radios.radio.add(0)
  elif container == 'ssids':
    return config_ap.ssids.ssid.add(default_ssid)
  elif container == 'bssids':
    return config_ap.ssids.ssid.add(default_ssid).bssids
  elif container == 'dot11r':
    return config_ap.ssids.ssid.add(default_ssid).dot11r
  elif container == 'band-steering':
    return config_ap.ssids.ssid.add(default_ssid).band_steering
  elif container == 'wmm':
    return config_ap.ssids.ssid.add(default_ssid).wmm
  elif container == 'ssh':
    return config_ap.system.ssh_server
  elif container == 'provision-aps':
    ap_manager_obj = ap_manager.openconfig_ap_manager()
    provision_oc = ap_manager_obj.provision_aps.provision_ap
    return provision_oc.add(ap.mac.upper())
  elif container == 'joined-aps':
    ap_manager_obj = ap_manager.openconfig_ap_manager()
    joined_oc = ap_manager_obj.joined_aps.joined_ap
    return joined_oc.add(ap.ap_name)


def GetContainerFromJson(ap, json_path, container):
  """Returns an OC object based on provided json file.

  Json must adhere to schema.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    json_path: (str) full path to JSON file.
    container: (str) a supported container within the model.

  Returns:
    Serialized OC Object (YANGBaseClass).

  Raises:
    UnsupportedContainerError: If container is not supported.
  """
  container = _GetContainer(ap, container)
  json_data = ''
  with open(json_path, 'rt') as data_file:
    json_data = data_file.read()

  return pybindJSONDecoder.load_ietf_json(json.loads(json_data), None,
                                          None, obj=container.config)


def CycleChannels(ap, radio_obj, five_g=True, width=20):
  """Cycles through all available channels.

  Channels are set on the object and config is sent to the AP.  Config leaf is
  then verified, followed by comparing all values in the state leaf vs config.
  It takes roughly ~50 secs per channel or ~22 minutes for all 20MHz.  Varies
  per vendor.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    radio_obj: (YANGBaseClass) OC radio container object.
    five_g: (bool) Whether target is 5GHz radio.
    width: (int) Channel width, eg. 20, 40, 80.
  """
  ap.radio_id = '0' if five_g else '1'
  ap.radio_freq = 'FREQ_5GHZ' if five_g else 'FREQ_2GHZ'
  path = _GetPathByContainer(ap, 'radios')

  channels = _GetChannelSet(five_g, width)
  for channel in channels:
    logging.info('Setting radio id %s to channel %s', ap.radio_id, channel)
    if not five_g:
      radio_obj.id = ap.radio_id
      radio_obj.operating_frequency = ap.radio_freq
    radio_obj.channel_width = width
    radio_obj.channel = channel
    radio_obj.id = ap.radio_id
    json_str = pybindJSON.dumps(radio_obj, mode='ietf')
    SetConfig(ap, xpath=path, json_str=json_str)
    _VerifyRadioContainer(ap, radio_obj, five_g)


def CycleTransmitPowers(ap, radio_obj, power_levels, five_g=True):
  """Cycles through the given power_levels.

  Powers are set on the object and config is sent to the AP.  Config leaf is
  then verified, followed by comparing all values in the state leaf vs config.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    radio_obj: (YANGBaseClass) OC radio container object.
    power_levels: (list) integers representing the radio transmit-power.
    five_g: (bool) Whether target is 5GHz radio.
  """
  ap.radio_id = '0' if five_g else '1'
  ap.radio_freq = 'FREQ_5GHZ' if five_g else 'FREQ_2GHZ'
  path = _GetPathByContainer(ap, 'radios')

  for power in power_levels:
    logging.info('Setting radio id %s to transmit-power %s', ap.radio_id, power)
    if not five_g:
      radio_obj.id = ap.radio_id
      radio_obj.operating_frequency = ap.radio_freq
    radio_obj.transmit_power = power
    json_str = pybindJSON.dumps(radio_obj, mode='ietf')
    SetConfig(ap, xpath=path, json_str=json_str)
    logging.info('Sent power of %s as %s to %s', power, json_str, path)
    _VerifyRadioContainer(ap, radio_obj, five_g)


@retry(exceptions=_ACCEPTABLE_ERRORS2, tries=30, delay=10, max_delay=300)
def DisableRadio(ap, radio_obj, five_g=True):
  """Disables radio.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    radio_obj: (YANGBaseClass) OC radio container object.
    five_g: (bool) Whether target is 5GHz radio.

  Raises:
    ConfigError: if radio config does not match.
    StateMismatchError: if the radio did not get disabled.
  """
  ap.radio_id = '0' if five_g else '1'
  ap.radio_freq = 'FREQ_5GHZ' if five_g else 'FREQ_2GHZ'
  path = _GetPathByContainer(ap, 'radios')
  logging.info('Setting radio id %s to disabled', ap.radio_id)

  if not five_g:
    radio_obj.id = ap.radio_id
    radio_obj.operating_frequency = ap.radio_freq
    radio_obj.channel = 1
  radio_obj.enabled = False
  json_str = pybindJSON.dumps(radio_obj, mode='ietf')
  SetConfig(ap, xpath=path, json_str=json_str)
  expected_config = pybindJSON.dumps(radio_obj, mode='ietf')  # string format.
  # We reset path in case some parameters changed based above.
  path = _GetPathByContainer(ap, 'radios')

  gnmi_response = GetPath(ap, path)
  json_bytes = gnmi_response.notification[0].update[0].val.json_ietf_val
  json_bytes = json_bytes.replace(b'openconfig-wifi-types:', b'')
  retrieved_config_obj = pybindJSONDecoder.load_ietf_json(
      json.loads(json_bytes), None, None, obj=radio_obj)
  retrieved_config = pybindJSON.dumps(retrieved_config_obj, mode='ietf')
  if expected_config != retrieved_config:
    logging.info(expected_config)
    logging.info(retrieved_config)
    raise ConfigError('Radio "%s" config does not match config sent' %
                      ap.radio_id)

  path = path.replace('/config', '/state')
  radio = _GetContainer(ap, 'radios')
  gnmi_response = GetPath(ap, path)
  json_bytes = gnmi_response.notification[0].update[0].val.json_ietf_val
  json_bytes = json_bytes.replace(b'openconfig-wifi-types:', b'')
  radio_state = pybindJSONDecoder.load_ietf_json(
      json.loads(json_bytes), None, None, obj=radio.state)
  if radio_state.enabled:
    raise StateMismatchError('Radio %s not disabled')

  logging.info('Radio "%s" was disabled', ap.radio_id)


def CheckPortIsOpen(ap, port=22):
  """Returns True if a TCP connection can be established."""
  # Note: This is an integration test, consider moving to integration section.
  try:
    s = socket.create_connection((ap.ap_name, port), 5)
  except socket.timeout:
    logging.info('Timeout connecting to port %s on AP: %s', port, ap.ap_name)
    return False
  else:
    s.close()

  return True


def ValidateJoinedAPs(ap):
  """Validates the joined-aps adheres to schema and returns a state object.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.

  Returns:
    YANGBaseClass object with data from the JSON /joined-aps/ state response.
  """
  joined_aps_obj = _GetContainer(ap, 'joined-aps')
  path = '/joined-aps/joined-ap[hostname=%s]/state' % ap.ap_name
  gnmi_response = GetPath(ap, path)
  json_bytes = gnmi_response.notification[0].update[0].val.json_ietf_val
  json_bytes = json_bytes.replace(b'openconfig-wifi-types:', b'')
  state = pybindJSONDecoder.load_ietf_json(
      json.loads(json_bytes), None, None, obj=joined_aps_obj.state)

  return state


def ValidateContainer(ap, container):
  """Validates a container adheres to schema and returns a state object.

  # TODO(xavier):  This function should aim to replace ValidateJoinedAPs.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    container: (str) a supported container within the model.

  Returns:
    YANGBaseClass object with data from the JSON state response.
  """
  container_obj = _GetContainer(ap, container)
  path = _GetPathByContainer(ap, container)
  has_state = False
  if '/config' in path:
    has_state = True
    path = path.replace('/config', '/state')
  gnmi_response = GetPath(ap, path)
  json_bytes = gnmi_response.notification[0].update[0].val.json_ietf_val
  json_bytes = json_bytes.replace(b'openconfig-wifi-types:', b'')
  if has_state:
    state = pybindJSONDecoder.load_ietf_json(
        json.loads(json_bytes), None, None, obj=container_obj.state)
  else:
    state = pybindJSONDecoder.load_ietf_json(
        json.loads(json_bytes), None, None, obj=container_obj)
  # print(pybindJSON.dumps(state, mode='ietf'))

  return state


def _GetPathByContainer(ap, container):
  """Returns OC config path based on a container name.

  Certain containers may require additional path values that should be passed
  as attributes of the AP object. eg. 'radios' may require ap.radio_id.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    container: (str) a supported container within the model.
  Returns:
    The container path as a string.
  Raises:
    UnsupportedContainerError: If container is not supported.
  """
  if container not in _SUPPORTED_CONTAINERS:
    raise UnsupportedContainerError('Container "%s" is not supported'
                                    % container)
  default_ssid = 'ChidoTestGuest'
  if container == 'radios':
    if ap.vendor == 'arista':
      return (_HOST_PATH % ap.ap_name + 'radios/radio[id=%s]'
              '[operating-frequency=%s]/config' % (ap.radio_id, ap.radio_freq))
    return _HOST_PATH % ap.ap_name + 'radios/radio[id=%s]/config' % ap.radio_id
  if container == 'ssids':
    return _HOST_PATH % ap.ap_name + 'ssids/ssid[name=%s]/config' % (
        default_ssid)
  if container == 'bssids':
    return _HOST_PATH % ap.ap_name + 'ssids/ssid[name=%s]/bssids' % (
        default_ssid)
  elif container == 'dot11r':
    return _HOST_PATH % ap.ap_name + 'ssids/ssid[name=%s]/dot11r/config' % (
        default_ssid)
  elif container == 'band-steering':
    return (_HOST_PATH % ap.ap_name + 'ssids/ssid[name=%s]/band-steering/config'
            % default_ssid)
  elif container == 'wmm':
    return _HOST_PATH % ap.ap_name + 'ssids/ssid[name=%s]/wmm/config' % (
        default_ssid)
  elif container == 'ssh':
    return _HOST_PATH % ap.ap_name + 'system/ssh-server/config'
  elif container == 'provision-aps':
    return '/provision-aps/provision-ap[mac=%s]/config' % ap.mac.upper()


def SetContainer(ap, container, config_obj):
  """Sets a container config and verifies it based on config obj provided.

  This function works where setting and verifying the container does not require
  any special logic.  It simply sets configuration at a container level and
  verifies all the configured leafs' state.  All leafs are checked against
  schema.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    container: (str) a supported container within the model.
    config_obj: (YANGBaseClass) OC config object matching the container.
  Raises:
    ConfigError: If the config leaf does not match config sent.
  """
  path = _GetPathByContainer(ap, container)
  json_str = pybindJSON.dumps(config_obj, mode='ietf')
  SetConfig(ap, xpath=path, json_str=json_str)
  expected_config = pybindJSON.dumps(config_obj, mode='ietf')
  gnmi_response = GetPath(ap, path)

  json_bytes = gnmi_response.notification[0].update[0].val.json_ietf_val
  json_bytes = json_bytes.replace(b'openconfig-wifi-types:', b'')
  retrieved_config_obj = pybindJSONDecoder.load_ietf_json(
      json.loads(json_bytes), None, None, obj=config_obj)
  retrieved_config = pybindJSON.dumps(retrieved_config_obj, mode='ietf')
  if expected_config != retrieved_config:
    logging.info('Expected:\n%s', expected_config)
    logging.info('Retrieved:\n%s', retrieved_config)
    raise ConfigError('Container config does not match config sent')

  # Now verify the state.
  path = path.replace('/config', '/state')
  configured_keys = json.loads(expected_config).keys()
  # We replace the 'openconfig-*' prefix in JSON to get the actual leaf names.
  # TODO(xavier): Regex match prefix replace so it works for all models.
  leafs = [l.replace('openconfig-access-points:', '').replace(
      'openconfig-ap-manager:', '').replace('-', '_')
           for l in configured_keys]
  _VerifyContainerState(ap, container, path, leafs, retrieved_config_obj)


@retry(exceptions=_ACCEPTABLE_ERRORS, tries=30, delay=10, max_delay=300)
def _VerifyContainerState(ap, container, path, leafs, config_obj):
  """Verifies a given OC container given a list of leaves.

  The check is retried using a fuzzy incremental backoff.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    container: (str) name of the container to be verified.
    path: (str) Explicit OpenConfig tree state xpath.
    leafs: (list) Every leaf configured to verify against state.
    config_obj: (YANGBaseClass) OC config container object from AP.
  Raises:
    StateMismatchError: When a state leaf does not match expected values.
  """
  yang_obj = _GetContainer(ap, container)
  gnmi_response = GetPath(ap, path)
  json_bytes = gnmi_response.notification[0].update[0].val.json_ietf_val
  json_bytes = json_bytes.replace(b'openconfig-wifi-types:', b'')
  state_obj = pybindJSONDecoder.load_ietf_json(
      json.loads(json_bytes), None, None, obj=yang_obj.state)
  # Verify the configured values to the state values.
  _CompareLeafs(ap, leafs, config_obj, state_obj)


def _CompareLeafs(ap, leafs, config_container, state_container):
  """Compares leafs in a container from config vs state.

  The expectation is that all configured leafs must match state leafs values.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    leafs: (list) Every leaf name configured to verify against state.
    config_container: (YANGBaseClass) OC config container object.
    state_container: (YANGBaseClass) OC state container object.

  Raises:
    StateMismatchError: When a state leaf does not match expected values.
  """
  for leaf in leafs:
    c_val = getattr(config_container, leaf)
    s_val = getattr(state_container, leaf)
    if c_val != s_val:
      logging.info('Leaf "%s" mismatch on AP %s.  Expected "%s", '
                   'got "%s"', leaf, ap.ap_name, c_val, s_val)
      raise StateMismatchError('Leaf "%s" mismatch on AP %s.  Expected "%s", '
                               'got "%s"' % (leaf, ap.ap_name, c_val, s_val))
  logging.info('Config leafs matched in state for AP %s: %s', ap.ap_name, leafs)


def _GetChannelSet(five_g, width):
  """Returns a tuple of target channels based on spectrum and width given.

  Args:
    five_g: (bool) Whether target is 5GHz radio.
    width: (int) Channel width, eg. 20, 40, 80.
  """
  if five_g:
    if width == 20:
      return (36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 116, 120, 124,
              128, 132, 136, 140, 144, 149, 153, 157, 161, 165)
    elif width == 40:
      return (36, 44, 52, 60, 100, 108, 116, 124, 132, 140, 149, 157)
    elif width == 80:
      return (36, 52, 100, 116, 132, 149)

  # we return 2.4G channels otherwise.
  return (1, 6, 11)


def _VerifyRadioContainer(ap, radio_obj, five_g=True):
  """Verifies the config and state leafs ensuring they match the sent config.

  Args:
    ap: (object) chido_test.ApObject containing all AP attributes.
    radio_obj: (YANGBaseClass) OC radio config container object.
    five_g: (bool) Whether target is 5GHz radio.
  Raises:
    ConfigError: If the config leaf does not match config sent.
  """
  # Check the config leaf.
  expected_config = pybindJSON.dumps(radio_obj, mode='ietf')  # string format.
  ap.radio_id = '0' if five_g else '1'
  ap.radio_freq = 'FREQ_5GHZ' if five_g else 'FREQ_2GHZ'
  path = _GetPathByContainer(ap, 'radios')

  gnmi_response = GetPath(ap, path)

  json_bytes = gnmi_response.notification[0].update[0].val.json_ietf_val
  json_bytes = json_bytes.replace(b'openconfig-wifi-types:', b'')
  retrieved_config_obj = pybindJSONDecoder.load_ietf_json(
      json.loads(json_bytes), None, None, obj=radio_obj)
  retrieved_config = pybindJSON.dumps(retrieved_config_obj, mode='ietf')
  if expected_config != retrieved_config:
    logging.info('Expected:\n%s', expected_config)
    logging.info('Retrieved:\n%s', retrieved_config)
    raise ConfigError('Radio "%s" config does not match config sent' %
                      ap.radio_id)

  # Now verify the state.
  path = path.replace('/config', '/state')
  configured_keys = json.loads(expected_config).keys()
  leafs = [l.replace('openconfig-access-points:', '').replace('-', '_')
           for l in configured_keys]
  _VerifyContainerState(ap, 'radios', path, leafs, retrieved_config_obj)


def Deserialize(ap, gnmi_response, del_messages=True):
  """Checks if a given json can be deserialized by adhering to schema."""
  # TODO(xavier): Figure out if an option to pull high level containers of
  # hostname, radios, ssids, system, assigned_ap_managers makes sense.
  ap_base = v020binding.openconfig_access_points()
  if ap.vendor == 'arista':
    ap_base = arista_aps.openconfig_access_points()
  ap_obj = ap_base.access_points.access_point.add(ap.ap_name)

  # TODO(xavier): Figure out why pybindJSONDecoder needs this workaround.
  json_bytes = gnmi_response.notification[0].update[0].val.json_ietf_val
  json_bytes = json_bytes.replace(b'openconfig-aaa:', b'')
  json_bytes = json_bytes.replace(b'openconfig-wifi-types:', b'')
  json_dict = json.loads(json_bytes)
  if del_messages:
    # Delete inconsistently implemented model. Test separately.
    json_dict['openconfig-access-points:system'].pop('messages', None)

  binded_obj = pybindJSONDecoder.load_ietf_json(json_dict, None, None,
                                                obj=ap_obj)
  # print(pybindJSON.dumps(binded_obj, mode='ietf'))

  return binded_obj


def _GetUserPass(vendor):
  """Returns username and password as a tuple given a vendor string."""
  username, password = '', ''
  if vendor in ('aruba', 'arista'):
    username, password = 'admin', 'admin'
  else:
    username = _GetKey('mist_user')
    password = _GetKey('mist_pass')

  return username, password


def _GetKey(key_name):
  """Gets key from keystore/local, ensuring the return value is a text type."""
  # TODO(xavierc):  Store keys somehwere.
  if key_name == 'mist_pass' or key_name == 'mist_user':
    try:
      key = chido_secrets.mist_pass if key_name == 'mist_pass' else chido_secrets.mist_user
      logging.info('Got key through local secrets')
      return key
    except NameError:
      logging.error('Unable to get key from local secrets')

  raise GetKeyError('Unable to obtain key: %s' % key_name)
