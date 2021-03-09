import time
import unittest

from absl import logging  # pip install absl-py
import chido


_FILES = 'testdata/'
# OC Paths
_HOST_PATH = '/access-points/access-point[hostname=%s]/'


class ApObject(object):
  """Represents an access point."""

  def __init__(self, ap_name):
    """Initializes a AP Object with given attributes.

    Args:
      ap_name: (str) name of the access point.
    """
    self.ap_name = ap_name
    self.targetip = None
    self.targetipv6 = None
    self.targetport = None
    self.mac = None
    self.model = None
    self.opstate = None
    self.power_source = None
    self.serial = None
    self.stub = None
    self.vendor = ''


class ChidoTest(unittest.TestCase):

  def setUp(self):
    super(ChidoTest, self).setUp()

    self.ap_arista = ApObject(
        'ap-02-102.example.com')
    self.ap_mist = ApObject(
        'ap-02-100.example.com')
    self.ap_aruba = ApObject(
        'ap-02-104.example.com')
    ap_objs = [self.ap_arista, self.ap_aruba, self.ap_mist]

    for ap_obj in ap_objs:
      if ap_obj is self.ap_arista:
        ap_obj.mac = '30:86:2D:25:26:27'
        ap_obj.vendor = 'arista'
        ap_obj.targetport = '8080'
        ap_obj.targetip = '100.77.250.242'
        ap_obj.targetipv6 = '2001:15c:33:10:3286:2dff:fe25:e61f'
        ap_obj.model = 'C-130'
        ap_obj.opstate = 'UP'
        ap_obj.power_source = 'AT'
        ap_obj.serial = '12330862D25E'
      elif ap_obj is self.ap_mist:
        ap_obj.mac = '5C:5B:35:01:02:03'
        ap_obj.vendor = 'mist'
        ap_obj.targetport = '443'
        ap_obj.targetip = '100.66.236.21'
        ap_obj.targetipv6 = ''
        ap_obj.model = 'AP41'
        ap_obj.opstate = 'UP'
        ap_obj.power_source = 'AT'
        ap_obj.serial = '1231001117020'
      elif ap_obj is self.ap_aruba:
        ap_obj.mac = '48:4A:E9:CC:CB:CA'
        ap_obj.vendor = 'aruba'
        ap_obj.targetport = '10162'
        ap_obj.targetip = '100.66.236.4'
        ap_obj.targetipv6 = '2001:15c:33:11:4a4a:e9ff:fec3:9db4'
        ap_obj.model = 'AP-345-US'
        ap_obj.opstate = 'UP'
        ap_obj.power_source = 'AT'
        ap_obj.serial = '123CNH1K51'

  def tearDown(self):
    super(ChidoTest, self).tearDown()
    time.sleep(2)


class AristaTest(ChidoTest):

  def test001BaseConfigOfficeArista(self):
    # Ensures an office config is accepted.
    self.assertTrue(chido.SetConfig(self.ap_arista,
                                    _FILES + 'arista_office_base_full.json'))

  def test002BaseConfigRFSiloArista(self):
    # Ensures an office + rf silo config is accepted.
    self.assertTrue(chido.SetConfig(self.ap_arista,
                                    _FILES + 'arista_office_silo_full.json'))

  def test003DeserializeArista(self):
    # Ensure full tree including state leaves are deserialized/adhere to schema.
    gnmi_response = chido.GetPath(self.ap_arista,
                                  _HOST_PATH % self.ap_arista.ap_name)
    chido.Deserialize(self.ap_arista, gnmi_response)

  def test004FiveRadio20Cycle(self):
    # Cycles through all 20MHz channels.
    radio = chido.GetContainerFromJson(
        self.ap_arista, _FILES + 'arista_radio_base.json', 'radios')
    chido.CycleChannels(self.ap_arista, radio)

  def test005FiveRadio40Cycle(self):
    # Cycles through all 40MHz channels.
    radio = chido.GetContainerFromJson(
        self.ap_arista, _FILES + 'arista_radio_base.json', 'radios')
    chido.CycleChannels(self.ap_arista, radio, width=40)

  def test006FiveRadio80Cycle(self):
    # Cycles through all 80MHz channels.
    radio = chido.GetContainerFromJson(
        self.ap_arista, _FILES + 'arista_radio_base.json', 'radios')
    chido.CycleChannels(self.ap_arista, radio, width=80)

  def test007TwoRadioCycle(self):
    # Test 2G radio channels.
    radio = chido.GetContainerFromJson(
        self.ap_arista, _FILES + 'arista_radio_base.json', 'radios')
    chido.CycleChannels(self.ap_arista, radio, five_g=False)

  def test008FiveRadioPowerCycle(self):
    # Cycles through some power levels (ie. 6, 10, 15)
    radio = chido.GetContainerFromJson(
        self.ap_arista, _FILES + 'arista_radio_base.json', 'radios')
    chido.CycleTransmitPowers(self.ap_arista, radio, [6, 10, 15])

  def test009FiveRadioDisable(self):
    radio = chido.GetContainerFromJson(
        self.ap_arista, _FILES + 'arista_radio_base.json', 'radios')
    chido.DisableRadio(self.ap_arista, radio)

  def test010TwoRadioDisable(self):
    radio = chido.GetContainerFromJson(
        self.ap_arista, _FILES + 'arista_radio_base.json', 'radios')
    chido.DisableRadio(self.ap_arista, radio, five_g=False)

  def test011SSIDBase(self):
    # Test basic SSID configuration with commonly used parameters.
    ssid = chido.GetContainerFromJson(self.ap_arista,
                                      _FILES + 'arista_ssid_base.json', 'ssids')
    chido.SetContainer(self.ap_arista, 'ssids', ssid)

  def test012SSIDAlternetate(self):
    # Similar to base but flip boolean parameters.
    ssid = chido.GetContainerFromJson(
        self.ap_arista, _FILES + 'arista_ssid_alternate.json', 'ssids')
    chido.SetContainer(self.ap_arista, 'ssids', ssid)

  # def test013Dot11rBase(self):
  #   dot11r = chido.GetContainerFromJson(self.ap_arista,
  #                                       _FILES + 'dot11r_base.json', 'dot11r')
  #   chido.SetContainer(self.ap_arista, 'dot11r', dot11r)

  def test014BandSteeringBase(self):
    band_steering = chido.GetContainerFromJson(
        self.ap_arista, _FILES + 'band_steering_base.json', 'band-steering')
    chido.SetContainer(self.ap_arista, 'band-steering', band_steering)

  # def test015WmmBase(self):
  #   wmm = chido.GetContainerFromJson(
  #       self.ap_arista, _FILES + 'wmm_base.json', 'wmm')
  #   chido.SetContainer(self.ap_arista, 'wmm', wmm)

  def test016DisableSSH(self):
    ssh = chido.GetContainerFromJson(self.ap_arista, _FILES + 'ssh_base.json',
                                     'ssh')
    chido.SetContainer(self.ap_arista, 'ssh', ssh)
    self.assertFalse(chido.CheckPortIsOpen(self.ap_arista, 22))

  def test017ProvisionUS(self):
    provision_aps = chido.GetContainerFromJson(
        self.ap_arista, _FILES + 'arista_provision_us.json', 'provision-aps')
    chido.SetContainer(self.ap_arista, 'provision-aps', provision_aps)

  def test018ValidateJoinedAPs(self):
    state = chido.ValidateJoinedAPs(self.ap_arista)
    self.assertEqual(state.hostname, self.ap_arista.ap_name)
    self.assertEqual(state.mac.upper(), self.ap_arista.mac)
    self.assertEqual(state.model, self.ap_arista.model)
    self.assertEqual(state.opstate, self.ap_arista.opstate)
    self.assertEqual(state.power_source, self.ap_arista.power_source)
    self.assertEqual(state.serial, self.ap_arista.serial)
    self.assertEqual(state.ipv4, self.ap_arista.targetip)
    self.assertEqual(state.ipv6, self.ap_arista.targetipv6)
    self.assertTrue(state.enabled)
    self.assertGreater(state.uptime, 1)


class ArubaTest(ChidoTest):

  def test001BaseConfigOfficeAruba(self):
    self.assertTrue(chido.SetConfig(self.ap_aruba,
                                    _FILES + 'aruba_office_base_full.json'))

  def test002BaseConfigRFSiloAruba(self):
    self.assertTrue(chido.SetConfig(self.ap_aruba,
                                    _FILES + 'aruba_office_silo_full.json'))

  def test003DeserializeAruba(self):
    gnmi_response = chido.GetPath(self.ap_aruba,
                                  _HOST_PATH % self.ap_aruba.ap_name)
    chido.Deserialize(self.ap_aruba, gnmi_response)

    # TODO(issue#): Aruba bug -- unable to set container.
#   def test004FiveRadio20Cycle(self):
#     radio = chido.GetContainerFromJson(
#         self.ap_aruba, _FILES + 'aruba_radio_base.json', 'radios')
#     chido.CycleChannels(self.ap_aruba, radio)

#   def test005FiveRadio40Cycle(self):
#     radio = chido.GetContainerFromJson(
#         self.ap_aruba, _FILES + 'aruba_radio_base.json', 'radios')
#     chido.CycleChannels(self.ap_aruba, radio, width=40)

#   def test006FiveRadio80Cycle(self):
#     radio = chido.GetContainerFromJson(
#         self.ap_aruba, _FILES + 'aruba_radio_base.json', 'radios')
#     chido.CycleChannels(self.ap_aruba, radio, width=80)

#   def test007TwoRadioCycle(self):
#     radio = chido.GetContainerFromJson(
#         self.ap_aruba, _FILES + 'aruba_radio_base.json', 'radios')
#     chido.CycleChannels(self.ap_aruba, radio, five_g=False)

#   def test008FiveRadioPowerCycle(self):
#     radio = chido.GetContainerFromJson(
#         self.ap_aruba, _FILES + 'aruba_radio_base.json', 'radios')
#     chido.CycleTransmitPowers(self.ap_aruba, radio, [6, 10, 15])

#   def test009FiveRadioDisable(self):
#     radio = chido.GetContainerFromJson(
#         self.ap_aruba, _FILES + 'aruba_radio_base.json', 'radios')
#     chido.DisableRadio(self.ap_aruba, radio)

#   def test010TwoRadioDisable(self):
#     radio = chido.GetContainerFromJson(
#         self.ap_aruba, _FILES + 'aruba_radio_base.json', 'radios')
#     chido.DisableRadio(self.ap_aruba, radio, five_g=False)

#   def test011SSIDBase(self):
#     ssid = chido.GetContainerFromJson(self.ap_aruba,
#                                       _FILES + 'aruba_ssid_base.json',
#                                       'ssids')
#     chido.SetContainer(self.ap_aruba, 'ssids', ssid)

#   def test012SSIDAlternetate(self):
#     ssid = chido.GetContainerFromJson(
#         self.ap_aruba, _FILES + 'aruba_ssid_alternate.json', 'ssids')
#     chido.SetContainer(self.ap_aruba, 'ssids', ssid)

#   def test013Dot11rBase(self):
#     dot11r = chido.GetContainerFromJson(self.ap_aruba,
#                                         _FILES + 'dot11r_base.json', 'dot11r')
#     chido.SetContainer(self.ap_aruba, 'dot11r', dot11r)

#   def test014BandSteeringBase(self):
#     band_steering = chido.GetContainerFromJson(
#         self.ap_aruba, _FILES + 'band_steering_base.json', 'band-steering')
#     chido.SetContainer(self.ap_aruba, 'band-steering', band_steering)

#   def test015WmmBase(self):
#     wmm = chido.GetContainerFromJson(
#         self.ap_aruba, _FILES + 'wmm_base.json', 'wmm')
#     chido.SetContainer(self.ap_aruba, 'wmm', wmm)

#  def test016DisableSSH(self):
#    ssh = chido.GetContainerFromJson(self.ap_aruba, _FILES + 'ssh_base.json',
#                                     'ssh')
#    chido.SetContainer(self.ap_aruba, 'ssh', ssh)
#    self.assertFalse(chido.CheckPortIsOpen(self.ap_aruba, 22))

  # def test017ProvisionUS(self):
  #   # TODO(issue#): This is broken in some firmwares.
  #   provision_aps = chido.GetContainerFromJson(
  #       self.ap_aruba, _FILES + 'aruba_provision_us.json', 'provision-aps')
  #   chido.SetContainer(self.ap_aruba, 'provision-aps', provision_aps)

  def test018ValidateJoinedAPs(self):
    state = chido.ValidateJoinedAPs(self.ap_aruba)
    self.assertEqual(state.hostname, self.ap_aruba.ap_name)
    self.assertEqual(state.mac.upper(), self.ap_aruba.mac)
    self.assertEqual(state.model, self.ap_aruba.model)
    self.assertEqual(state.opstate, self.ap_aruba.opstate)
    self.assertEqual(state.power_source, self.ap_aruba.power_source)
    self.assertEqual(state.serial, self.ap_aruba.serial)
    self.assertEqual(state.ipv4, self.ap_aruba.targetip)
    self.assertEqual(state.ipv6, self.ap_aruba.targetipv6)
    self.assertTrue(state.enabled)
    self.assertGreater(state.uptime, 1)


class MistTest(ChidoTest):

  def test001BaseConfigOfficeMist(self):
    self.assertTrue(chido.SetConfig(self.ap_mist,
                                    _FILES + 'mist_office_base_full.json'))

  def test002BaseConfigRFSiloMist(self):
    self.assertTrue(chido.SetConfig(self.ap_mist,
                                    _FILES + 'mist_office_silo_full.json'))

  def test003DeserializeMist(self):
    gnmi_response = chido.GetPath(self.ap_mist,
                                  _HOST_PATH % self.ap_mist.ap_name)
    chido.Deserialize(self.ap_mist, gnmi_response)

  def test004FiveRadio20Cycle(self):
    radio = chido.GetContainerFromJson(
        self.ap_mist, _FILES + 'mist_radio_base.json', 'radios')
    chido.CycleChannels(self.ap_mist, radio)

  def test005FiveRadio40Cycle(self):
    radio = chido.GetContainerFromJson(
        self.ap_mist, _FILES + 'mist_radio_base.json', 'radios')
    chido.CycleChannels(self.ap_mist, radio, width=40)

  def test006FiveRadio80Cycle(self):
    radio = chido.GetContainerFromJson(
        self.ap_mist, _FILES + 'mist_radio_base.json', 'radios')
    chido.CycleChannels(self.ap_mist, radio, width=80)

  def test007TwoRadioCycle(self):
    radio = chido.GetContainerFromJson(
        self.ap_mist, _FILES + 'mist_radio_base.json', 'radios')
    chido.CycleChannels(self.ap_mist, radio, five_g=False)

  def test008FiveRadioPowerCycle(self):
    # Note: Mist AP41 maxes out at 18 transmit-power.
    radio = chido.GetContainerFromJson(
        self.ap_mist, _FILES + 'mist_radio_base.json', 'radios')
    chido.CycleTransmitPowers(self.ap_mist, radio, [6, 10, 15])

  def test009FiveRadioDisable(self):
    radio = chido.GetContainerFromJson(
        self.ap_mist, _FILES + 'mist_radio_base.json', 'radios')
    chido.DisableRadio(self.ap_mist, radio)

  def test010TwoRadioDisable(self):
    radio = chido.GetContainerFromJson(
        self.ap_mist, _FILES + 'mist_radio_base.json', 'radios')
    chido.DisableRadio(self.ap_mist, radio, five_g=False)

  def test011SSIDBase(self):
    ssid = chido.GetContainerFromJson(self.ap_mist,
                                      _FILES + 'mist_ssid_base.json', 'ssids')
    chido.SetContainer(self.ap_mist, 'ssids', ssid)

  def test012SSIDAlternetate(self):
    ssid = chido.GetContainerFromJson(
        self.ap_mist, _FILES + 'mist_ssid_alternate.json', 'ssids')
    chido.SetContainer(self.ap_mist, 'ssids', ssid)

  def test013Dot11rBase(self):
    dot11r = chido.GetContainerFromJson(self.ap_mist,
                                        _FILES + 'dot11r_base.json', 'dot11r')
    chido.SetContainer(self.ap_mist, 'dot11r', dot11r)

  # TODO(issue#): Unsupported containers by Mist below.
  # def test014BandSteeringBase(self):
  #   band_steering = chido.GetContainerFromJson(
  #       self.ap_mist, _FILES + 'band_steering_base.json', 'band-steering')
  #   chido.SetContainer(self.ap_mist, 'band-steering', band_steering)

  # def test015WmmBase(self):
  #   wmm = chido.GetContainerFromJson(
  #       self.ap_mist, _FILES + 'wmm_base.json', 'wmm')
  #   chido.SetContainer(self.ap_mist, 'wmm', wmm)

  def test016DisableSSH(self):
    # N/A for Mist.
    pass

  def test017ProvisionUS(self):
    provision_aps = chido.GetContainerFromJson(
        self.ap_mist, _FILES + 'mist_provision_us.json', 'provision-aps')
    chido.SetContainer(self.ap_mist, 'provision-aps', provision_aps)

  # TODO(b/123654785): Mist does not support IPv6 well, so the response
  # deserialization fails for state.ipv6.
  # def test018ValidateJoinedAPs(self):
  #   state = chido.ValidateJoinedAPs(self.ap_mist)
  #   self.assertEqual(state.hostname, self.ap_mist.ap_name)
  #   self.assertEqual(state.mac.upper(), self.ap_mist.mac)
  #   self.assertEqual(state.model, self.ap_mist.model)
  #   self.assertEqual(state.opstate, self.ap_mist.opstate)
  #   self.assertEqual(state.power_source, self.ap_mist.power_source)
  #   self.assertEqual(state.serial, self.ap_mist.serial)
  #   self.assertEqual(state.ipv4, self.ap_mist.targetip)
  #   self.assertEqual(state.ipv6, self.ap_mist.targetipv6)
  #   self.assertTrue(state.enabled)
  #   self.assertGreater(state.uptime, 1)


if __name__ == '__main__':
  logging.set_verbosity(logging.INFO)
  unittest.main()
