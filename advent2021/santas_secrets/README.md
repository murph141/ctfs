# Credits

Thank you [Retr0id](https://twitter.com/david3141593) for putting together this challenge!

This follows the challenge for December 9th.

# Table of contents
1. [Starting off](#starting-off)
2. [Structure of the data](#structure-of-the-data)
3. [Unicode fun](#unicode-fun)
4. [Aside: iterating on approaches quickly](#aside-iterating-on-approaches-quickly)
4. [Initial program setup](#initial-program-setup)
5. [Bruteforcing the key](#bruteforcing-the-key)

## Starting off

To start off with, we're given [code](code/server.py) and a command `nc santassecrets.advent2021.overthewire.org 1209` to run.

In addition, we're given the following information about the level:

> Santa built a service to allow elves to encrypt secret data without having access to the keys.

Running the command, we get the following:

```console
$ nc santassecrets.advent2021.overthewire.org 1209
help

Welcome to Santa's Super-Secure Secret Storage Service

There are 8 write-only keyslots.
There are 8 read/write dataslots.

You can encrypt the data in a chosen dataslot,
with a key from a chosen keyslot.

Once a keyslot is written, it cannot be read back.
This allows the elves to securely process encrypted data,
without being able to access the keys.

For example, to encrypt the string "topsecretmessage"
with key deadbeefdeadbeefdeadbeefdeadbeef:

write_key 3 deadbeefdeadbeefdeadbeefdeadbeef hex
write_data 7 topsecretmessage ascii
encrypt 3 2 7
read_data 2


AVAILABLE COMMANDS:

help                               print this message
encrypt keyslot dest src           encrypt src dataslot with chosen keyslot, write the result to dest dataslot
read_data dataslot                 read a chosen dataslot
write_data dataslot data encoding  write data to a chosen dataslot
write_key keyslot data encoding    write data to a chosen keyslot
exit                               exit the session
```

We aren't presented with any text right away, but typing "help" yields a bunch of options that we have available to us.

Consulting the code we linked above, we can see that the commands listed above map to commands that are being used in the source code.

At a high level, we have a service where we're able to encrypt arbitrary data (which we can provide).
We are also able to read that data and provide keys to encrypt that data.
(Note that we can't read the keys.)

Before the service is started, the flag is written into the data along with a randomly generated key and then encrypted (and overwritten) with that key.
The core idea here is that since we can't read the key, we should be able to recover out data.

## Structure of the data

To keep this service running, the code has two byte arrays -- one for data and one for keys.
Each byte array has 8 "slots" (i.e. spots to write data) and each slot is 16 bytes long.
This results in a byte array of size 128 (8*16) for each.

When we write to either of these slots, we provide input that is validated by the server, then ultimately written to the slot we designated.

Input comes in two types: "hex" and "ascii."
With the former, we can provide a hex string (e.g. "11223344") that'll be converted accordingly and saved to the byte array.
With the latter, we can provide a string (e.g. "abcd") that'll be converted to ascii and saved to the byte array.
Importantly, both of these formats validate that the length of the input data matches what we'd expect (for hex, 32 characters, for ascii, 16 characters).

The overall data structure looks like the following. Note, only the first few slots are shown for brevity.

```
Data:

Slot:         0                1                2                ...
Byte array:   |----------------|----------------|----------------|

Keys:

Slot:         0                1                2                ...
Byte array:   |----------------|----------------|----------------|
```

## Unicode fun

Looking deeper at our input types, "ascii" becomes interesting.
In particular, when we check the data's length for "ascii," we check the length _before_ we convert to ascii.
This means that we can send unicode over the wire (e.g. "á") whose length will count as one character when checked but will expand when we convert to ascii (in this case, to "\xc3\xa1").

We can take advantage of this to write more than 16 characters of data and allow ourselves to overwrite values in the adjacent slot.

We could imagine something like the following playing out in an example where we overwrite data in slot 1 with data in slot 0:

```
Data (before write):

Slot:         0                1                2                ...
Byte array:   |----------------|xxxxxxxxxxxxxxxx|----------------|

Data (after write):

Slot:         0                1                2                ...
Byte array:   |YYYYYYYYYYYYYYYY|Yxxxxxxxxxxxxxxx|----------------|
```

## Aside: iterating on approaches quickly

To help us move quickly and iterate on approaches, we can copy the code given to us (with a few amendments) and run a server locally.
In my case, the server I ended up iterating on can be found [here](code/amended.py).

Things of interest that were added:
- Functionality to _read_ a key and printing of relevant data values
- A known flag to help validate the approach
- Removal of server timeout and command limit
- Various print statements to aid in debugging

With this in place, I was able to iterate relatively quickly on approaches.
In addition, I was able to develop locally (i.e. without internet), which was especially helpful given I had a flight planned.

## Initial program setup

We glossed over this above, but the program is initially setup with a key and the flag having been encrypted.

From the code, we see the following:

```python
se = SecurityEngine()

# provision keyslot 5 with a secure random key, and use it to encrypt the flag
# since keyslots are write-only, the flag cannot be recovered!
se.run_cmd(f"write_key 5 {os.urandom(SLOT_SIZE).hex()} hex")
se.run_cmd(f"write_data 0 {FLAG[:16]} ascii")
se.run_cmd(f"write_data 1 {FLAG[16:]} ascii")
se.run_cmd(f"encrypt 5 0 0")
se.run_cmd(f"encrypt 5 1 1")
```

What this translates to in English is:
1. Generate a random key and write to slot 5
2. Write the flag data to slots 0 and 1
3. Encrypt (and overwrite) the flag data with the key in slot 5

This means the state of the data looks like the following, provided:
- E = encrypted flag
- K = key

```
Data:

Slot:         0                1                2                ...
Byte array:   |EEEEEEEEEEEEEEEE|EEEEEEEEEEEEEEEE|----------------|

Data (after write):

Slot:         4                5                6                ...
Byte array:   |----------------|KKKKKKKKKKKKKKKK|----------------|
```

This means that we can _read_ the encrypted data, but not the key.
If we were somehow able to read the key, we'd be able to finish the challenge.

## Bruteforcing the key

Given the above, it feels like we should be able to easily bruteforce the key.
The idea would be to do the following:
1. Encrypt some known data (e.g. 'A'*16) with the key
2. Write a key to slot 4 and overwrite into slot 5 with one character
   - Ensure the character we overwrite starts at 0x00
3. Encrypt the same known data from 1. with the new key
4. Check if the newly encrypt data matches the known good encryption from 1
5. If the data matches, we've found our first character, if not, go to step 2 and incremement the value we overwrite with
6. Rinse and repeat for the remaining character

This _would_ work in many cases, but a detail we didn't discuss yet was command limit.
The server was programmed to accept 1000 commands max.
In our case, we'd greatly exceed our quota, causing the connection to get closed and a new key to be generated.

We can take what we've got above and work backwards though.
The idea will be similar to above, but allows us to stay under the command limit.
Namely, it would entail:
1. Note the encrypted flag values
2. Encrypt some known data (e.g. 'A'*16) with the key
3. Overwrite the key with a character
4. Encrypt the known data with the new key
5. Note down the resulting encrypted value
6. Continue steps 2-4 until the entirety of key slot 5 is overwritten
   - Ensure that each iteration increases the overwrite by **one** byte
7. There will now be 16 encrypted values and one slot of known data
8. Working backwards, when 15 characters of the key were overwritten, we can _bruteforce_ the final value in the key by testing all values and running it through AES
9. Continue working backwards (one characer at a time) until all 16 characters are recovered
10. Use the key plus the encrypted flag values to decrypt the flag

This reduces our commands significantly since we perform the bruteforce on _our_ side (i.e. in code) as opposed to doing it on the server side where it'll consume commands (plural: we need to write, encrypt, and read for each bruteforced value).

After 15 overwrites, the data would look like the following, provided:
- E = encrypted flag
- a = known data
- A = encrypted known data
- O = overwritten key
- K = original key

```
Data:

Slot:         0                1                2                3                ...
Byte array:   |EEEEEEEEEEEEEEEE|EEEEEEEEEEEEEEEE|aaaaaaaaaaaaaaaa|AAAAAAAAAAAAAAAA|

Data (after write):

Slot:         4                5                6                ...
Byte array:   |OOOOOOOOOOOOOOOO|OOOOOOOOOOOOOOOK|----------------|
```

Once all of this is done, we end up with our: `AOTW{n0oO_d0nt_0v3rfl0w_my_bufs}`
