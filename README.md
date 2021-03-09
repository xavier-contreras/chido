# Chido
**Chido** is an Open source framework for testing OpenConfig enabled devices.

The aim is verifying OC schema and device functionality. There’s a strong
reliance on PyangBind’s pybindJSON and pybindJSONDecoder for serializing and
deserializing JSON. Using this method provides schema validation ‘for free’.
The majority of the framework works on a per yang container basis. The intended
JSON configuration is in a file, which is read from source and sent to the
device along with the name of the container.

Once pushed, the container from the device is compared to the pushed
configuration and an exact match is expected (ie. running configuration matches
sent configuration).

The state of the container is then polled from the device and the response is
deserialized into a PyangBind class ensuring adherence to schema. All the
configured leafs are then checked for exact match (ie. running configuration
matches reported operating state).

For state-only containers; a deserialization-only check is done, or optionally
can also return a PyangBind class and the test logic can verify values against
expected values.

**Note:** This initial commit is a geared towards wireless access point devices,
      though methods and general structure are built generically to allow growth.

Upcoming development priorities:
1.  Make device-type agnostic (ie. have device roles and role-specific tests)
2.  Add a "config file" type structure to take the target parameters.
3.  Make debugging failures simpler.
4.  Structure generated bindings to allow easier understanding of the source
    models used to generate them (model versioning).
5.  Add samples/tests for non-wifi devices.

## Running Tests

Since the tests are simply unit tests, this may be familiar to a lot of people.

### Running all tests under a class

Provide the class name.

```
python3 -m unittest -v chido_test.MistTest
test001BaseConfigOfficeMist (chido_test.MistTest) ... ok
test002BaseConfigRFSiloMist (chido_test.MistTest) ... ok
test003DeserializeMist (chido_test.MistTest) ... ok
test004FiveRadio20Cycle (chido_test.MistTest) ... ok
test005FiveRadio40Cycle (chido_test.MistTest) ... ok
test006FiveRadio80Cycle (chido_test.MistTest) ... ok
test007TwoRadioCycle (chido_test.MistTest) ... WARNING:retry.api:Leaf "channel" mismatch on AP zz-tri-esdn04-02-100.n.corp.google.com.  Expected "1", got "11", retrying in 10 seconds...
WARNING:retry.api:Leaf "channel" mismatch on AP zz-tri-esdn04-02-100.n.corp.google.com.  Expected "1", got "11", retrying in 10 seconds...
ok
test008FiveRadioPowerCycle (chido_test.MistTest) ... ERROR
test009FiveRadioDisable (chido_test.MistTest) ... WARNING:retry.api:Radio "0" config does not match config sent, retrying in 10 seconds...
ok
test010TwoRadioDisable (chido_test.MistTest) ... ok
test011SSIDBase (chido_test.MistTest) ... ok
test012SSIDAlternetate (chido_test.MistTest) ... ERROR
test013Dot11rBase (chido_test.MistTest) ... ok
test016DisableSSH (chido_test.MistTest) ... ok
test017ProvisionUS (chido_test.MistTest) ... ok
```

### Running a single test

Running a specific test can be done by providing the test class name and test
name.

```
python3 -m unittest -v chido_test.AristaTest.test005FiveRadio40Cycle
test005FiveRadio40Cycle (chido_test.AristaTest) ... importing the ABCs from 'collections' instead of from 'collections.abc' is deprecated since Python 3.3, and in 3.9 it will stop working
  class TypedList(collections.MutableSequence):
WARNING:retry.api:Leaf "channel" mismatch on AP zz-tri-esdn04-02-102.n.corp.google.com.  Expected "44", got "36", retrying in 10 seconds...
WARNING:retry.api:Leaf "channel" mismatch on AP zz-tri-esdn04-02-102.n.corp.google.com.  Expected "44", got "36", retrying in 10 seconds...
WARNING:retry.api:Leaf "channel" mismatch on AP zz-tri-esdn04-02-102.n.corp.google.com.
ok

----------------------------------------------------------------------
Ran 1 test in 100.697s

OK
```

## Getting started

### Installation
```
pip3 install -r requirements.txt
```

When running, if you see an error as below:
```
TypeError: Couldn't build proto file into descriptor pool!
gnmi_ext.proto: Import "gnmi_ext.proto" has not been loaded.
```

You may need this export statement:
```
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION='python'
```
This **may** also be worked around by:
```
pip uninstall protobuf
pip install --no-binary=protobuf protobuf
```

#### OS Specific Issues

**Mac OSX**
OSX may require XCode, use "xcode-select --install" to install xcode.

**Debian**
Debian may require the following if there's installation errors.
```
sudo apt-get install python3-dev
sudo apt-get install build-essential
```

### Update configuration
In lieu of a configuration file -- parameters are currently static in code, the
following needs to be manually set.

#### Update target parameters
Note that only the first item is strictly required -- others should be verified.

* Update target(s) parameters in chido_test.py under setUp.
* Verify/update `_MIST_GCP` constant under chido.py if Mist target endpoint is different.
* Verify/update constants.py if required.
* Verify/update testdata/\*.json files with relevant to your setup.

### Updating bindings
The bindings included here are the latest supported by each vendor.  These can
be summarized by the model versioning below.

```
OC_MODEL_VERSION_TUNNEL = {
    'arista':
        {
            'openconfig-access-points-yang': '0.3.0',
            'openconfig-ap-manager-yang': '0.1.1',
            'openconfig-wifi-mac-yang': '0.4.0',
            'openconfig-wifi-phy-yang': '0.4.0',
            'openconfig-wifi-types-yang': '0.1.1'
        },
    'aruba':
        {
            'openconfig-access-points-yang': '0.2.0',
            'openconfig-ap-manager-yang': '0.1.1',
            'openconfig-wifi-mac-yang': '0.3.0',
            'openconfig-wifi-phy-yang': '0.2.0',
            'openconfig-wifi-types-yang': '0.1.0'
        },
    'mist':
        {
            'openconfig-access-points-yang': '0.2.0',
            'openconfig-ap-manager-yang': '0.1.1',
            'openconfig-wifi-mac-yang': '0.3.0',
            'openconfig-wifi-phy-yang': '0.2.0',
            'openconfig-wifi-types-yang': '0.1.0'
        }
}
```

Refer to the pybind and pyang docs for reference on creating new bindings, ie.~
```
pyang -p ../ --plugindir /usr/local/lib/python2.7/dist-packages/pyangbind/plugin/ -f pybind -o access_points_bindings.py wifi/access-points/openconfig-access-points.yang
```
