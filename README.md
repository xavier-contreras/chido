# chido
Open source test framework for OpenConfig enabled devices.

The aim is verifying OC schema and device functionality. There’s a strong
reliance on pyangbind’s pybindJSON and pybindJSONDecoder for serializing and
deserializing JSON. Using this method provides schema validation ‘for free’.
The majority of the framework works on a per yang container basis. The intended
JSON configuration is in a file, which is read from source and sent to the
device along with the name of the container.

Once pushed, the container from the device is compared to the pushed
configuration and an exact match is expected (ie. running configuration matches
sent configuration).

The state of the container is then polled from the device and the response is
deserialized into a pyangbind class ensuring adherence to schema. All the
configured leafs are then checked for exact match (ie. running configuration
matches reported operating state).

For state-only containers; a deserialization-only check is done, or optionally
can also return a pyangbind class and the test logic can verify values against
expected values.

Note: This initial commit is a geared towards wireless access point devices,
      though methods and general structure are built generically to allow growth.

Upcoming development priorities:
1.  Make device-type agnostic (ie. have device roles and role-specific tests)
2.  Add a "config file" type structure to take the target parameters.
3.  Make debugging failures simple.
4.  Structure generated bindings to allow easier understanding of the source
    models used to generate them (model versioning).
5.  Add samples/tests for non-wifi devices.
