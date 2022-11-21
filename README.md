# LEAP ISA Model

Apple SoCs including

 * M1 (t8103)
 * M1 Pro/Max (t6000/t6001)
 * M2 (t8112)

and possibly other iPhone/AirPod chips contain a signal processor called the LEAP. This repository holds a (work in progress) description of the processor's ISA, mostly in the form of a [Python model](https://github.com/povik/leap-isa/blob/master/model.py). So far no differences between the LEAP instances on different chips have been encountered.

On M1 the LEAP instance runs at the order of 300 MIPS. A few LEAP cores is packed into a LEAP cluster.

## Overview

The architectural state of the processor appears to comprise of the content of a couple of huge, general-purpose register banks, and a program counter.

At a high level, when a program is loaded, a few 'routines' (specified by means of PC mantinels) are configured into the processor from the outside. Within a routine there's no (non-trivial) control flow.

The core does in-order execution. There's an observable pipeline stall if the result of a complex operation (notably `FMULTACC`) is reused as an operand by the instruction that follows just after.

### Banks

There are four banks of 32-bit registers. Bank 0 has 4096 registers, banks 1 to 3 have 3072. On execution of an instruction one value is retrieved from each of the banks and is available as an operand. That means an operation cannot source two or more operands from the same bank.

Bank 0 is special and its use is yet to be fully figured out.

### I/O Ports

To exchange data with the outside world, the LEAP cluster has I/O ports numbered in the space from 0x0 to 0x80. The ports are simple 32-bit registers with adjacent full/empty signaling (a 1-bit flag). Both LEAP routines and peripherals can write and read the port registers and toggle the full/empty flag.

As part of a LEAP program, specific routines are configured to execute once certain ports are empty and certain ports are full. Since ports can be used for inter-routine communication, and there are instructions for *conditional* reading and writing of ports, this way one builds up more interesting control flow among the routines.

### Instructions

An instruction is encoded in four parts. Each part belongs to a separate instruction memory block. Let's label them:

    A, B, C, D

 * *B*, *C* and *D* specify the indices at which a value is to be retrieved from banks 1, 2, 3 respectively.

 * *A* is where the opcode, operand routing and result placement is encoded in.

## Testing

There's some 20000 testcases in `testing/corpus.gz`. They are samples of the state before and after the execution of random instructions taken from some sensible subset of the instruction space.

To test the model (`model.py`) on the corpus, run the following from the root of the repository:

    gzip -d < testing/corpus.gz | PYTHONPATH=.:$PYTHONPATH python3 testing/run.py

On the last line of the output, it will print: the number of well predicted testcases/badly predicted testcases/number of all testcases. Testcases for which the model raises `NotImplementedError` are considered neither well- nor badly-predicted.

Pull requests are automatically labeled by the change in the test score they cause.

## Contributions & License

Contributions are welcome. Contents of this repository (including any contributions!) are published under the terms of the MIT license, see the `LICENSE` file.
