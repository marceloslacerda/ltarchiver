# Ltarchiver

## Store command

```
store <source> <destination>
```

Steps to store:

1. Create metadata structure if it does not exist.
2. Write the source and the destination (with blkid) into the bookeeping record.
3. Calculate checksum write to record and destination device.
4. Transfer data with cp.
5. Check checksum on destination.
6. Sync.
7. Calculate reed-solomon code.
8. Write reed-solomon code.
9. Check reed-solomon code.
10. Sync.
11. Write commit on the bookkeeping record.

https://github.com/tomerfiliba/reedsolomon