------------------------------- MODULE IdAllocation -------------------------------
\* valid as of 965ac21; not maintained.
\* SPIKE-003 part 2: the FIXED index-store protocol (DEC-093, DDD-034, STORY-696).
\* Disposable model. Not shipped, not a verify contract, never run in CI.
\*
\* One artifact type. Canonical ids are 1..MaxNum; draft ids are 101..100+NDrafts.
\* A file is a record [id |-> frontmatter id, ino |-> inode]; `files` maps a file
\* NAME (stem) to its record, so a hard link is two names with one ino.
\* Every locked command is one atomic step except where the code performs several
\* guarded writes a crash can separate (create: file then index; renumber:
\* journal, per-file rewrite, index rewrite, link, unlink, rebuild, journal delete).
EXTENDS Naturals, FiniteSets, TLC

CONSTANTS Actors,      \* concurrent specflow processes
          MaxNum,      \* largest canonical id
          NDrafts,     \* number of distinct draft ids
          MaxIno,      \* bound on files ever created (keeps the state space finite)
          MaxCrashes,  \* bound on crashes
          MergeKinds,  \* subset of {"Conflict","Ours","Theirs","Union"}
          Branches,    \* subset of {"main","feature","detached"}
          Ops,         \* enabled actions, for the variant configs
          CandidateFix \* TRUE: a proposed repair, NOT the shipped code: every
                       \* allocator also floors on the renumber journal's targets
                       \* and on every frontmatter id (not only file stems)

Nums   == 1..MaxNum
Drafts == 101..(100 + NDrafts)
IsDraft(n) == n > 100
NumsIn(S) == {x \in S : ~IsDraft(x)}
Max(S) == IF S = {} THEN 0 ELSE CHOOSE x \in S : \A y \in S : x >= y
Min(S) == CHOOSE x \in S : \A y \in S : x <= y
None == "none"
NoMap == [x \in {} |-> 0]
Idx0 == [ok |-> TRUE, keys |-> {}, next |-> 1]
Loc0 == [idx |-> Idx0, map |-> NoMap, src |-> 0]

VARIABLES files,       \* name -> [id, ino]
          index,       \* [ok, keys, next]; ok = FALSE is a conflict-marked index
                       \* whose keys/next are the salvage of both sides
          quarantine,  \* ids kept by rebuild for fileless index entries
          journal,     \* renumber journal: draft id -> target id (empty = absent)
          forkIdx,     \* the index the other branch forked from (for GitMerge)
          branch,
          lock,        \* the repo-wide mutation lock (abstract mutex; flock)
          pc, loc,     \* per-actor program counter and locals
          allocated,   \* history: canonical ids ever allocated
          reuse,       \* observer: an allocation picked an id in `allocated`
          clobber,     \* observer: a write that must create a name replaced one
          dirty,       \* a crash or environment edit happened since the last rebuild
          crashes, nextIno,
          rnBad,       \* observer: a renumber ended stuck or not converged
          draftsUsed   \* draft ids ever generated (hash of title + timestamp:
                       \* never generated twice)

vars == <<files, index, quarantine, journal, forkIdx, branch, lock, pc, loc,
          allocated, reuse, clobber, dirty, crashes, nextIno, rnBad, draftsUsed>>

FmIds == {files[n].id : n \in DOMAIN files}
AllIdle == \A a \in Actors : pc[a] = "idle"
Put(f, n, c) == [m \in DOMAIN f \cup {n} |-> IF m = n THEN c ELSE f[m]]
Drop(f, n) == [m \in DOMAIN f \ {n} |-> f[m]]

\* Extra allocation floor under CandidateFix (empty for the shipped protocol).
Promised == IF CandidateFix THEN {journal[d] : d \in DOMAIN journal} \cup NumsIn(FmIds) ELSE {}

\* _rebuild_dir_index: keys from frontmatter ids on disk; fileless keys go to the
\* quarantine; next_id floors on quarantine and the old next_id (DEF-007 fix).
RebuiltQ == quarantine \cup (index.keys \ FmIds)
RebuiltIdx == [ok |-> TRUE, keys |-> FmIds,
               next |-> Max(NumsIn(FmIds) \cup NumsIn(RebuiltQ) \cup {index.next - 1}
                            \cup Promised) + 1]
\* _read_index: a conflicted index is rebuilt under the lock (DEF-006 fix).
HIdx == IF index.ok THEN index ELSE RebuiltIdx
HQ   == IF index.ok THEN quarantine ELSE RebuiltQ
HDirty == IF index.ok THEN dirty ELSE FALSE

Init ==
  /\ files = [x \in {} |-> [id |-> 0, ino |-> 0]]
  /\ index = Idx0 /\ quarantine = {} /\ journal = NoMap /\ forkIdx = Idx0
  /\ branch = "main" /\ lock = None
  /\ pc = [a \in Actors |-> "idle"] /\ loc = [a \in Actors |-> Loc0]
  /\ allocated = {} /\ reuse = FALSE /\ clobber = FALSE /\ dirty = FALSE
  /\ crashes = 0 /\ nextIno = 1 /\ rnBad = FALSE /\ draftsUsed = {}

---------------------------------------------------------------------------------
\* create: under the lock, heal, allocate max(stems, healed index keys, quarantine,
\* next_id - 1) + 1, skip taken names, exclusive_write the file (linearisation
\* point); then write the index.
CreateAlloc(a) ==
  /\ "Create" \in Ops /\ pc[a] = "idle" /\ lock = None /\ nextIno <= MaxIno
  /\ LET I == HIdx
         healed == I.keys \cup {files[n].id : n \in {m \in DOMAIN files : m \notin I.keys}}
         floor == Max(NumsIn(DOMAIN files) \cup NumsIn(healed) \cup NumsIn(HQ) \cup {I.next - 1}
                      \cup Promised)
         freeNums == {k \in (floor + 1)..MaxNum : k \notin healed /\ k \notin DOMAIN files}
         cands == IF branch = "feature" THEN Drafts \ (DOMAIN files \cup healed \cup draftsUsed)
                  ELSE IF freeNums = {} THEN {} ELSE {Min(freeNums)}
     IN \E new \in cands :
          /\ clobber' = (clobber \/ new \in DOMAIN files)
          /\ files' = Put(files, new, [id |-> new, ino |-> nextIno])
          /\ nextIno' = nextIno + 1
          /\ draftsUsed' = IF IsDraft(new) THEN draftsUsed \cup {new} ELSE draftsUsed
          /\ reuse' = (reuse \/ new \in allocated)
          /\ index' = I /\ quarantine' = HQ /\ dirty' = HDirty
          /\ lock' = a
          /\ pc' = [pc EXCEPT ![a] = "c_idx"]
          /\ loc' = [loc EXCEPT ![a].idx =
                       [ok |-> TRUE, keys |-> healed \cup {new},
                        next |-> IF IsDraft(new) THEN I.next ELSE Max({I.next, new + 1})],
                             ![a].src = new]
  /\ UNCHANGED <<journal, forkIdx, branch, crashes, rnBad, allocated>>

\* The id counts as allocated (history) when create reports success; an id whose
\* create crashed before reporting was never handed to anyone.
CreateIdx(a) ==
  /\ pc[a] = "c_idx"
  /\ index' = loc[a].idx
  /\ allocated' = IF IsDraft(loc[a].src) THEN allocated ELSE allocated \cup {loc[a].src}
  /\ lock' = None /\ pc' = [pc EXCEPT ![a] = "idle"] /\ loc' = [loc EXCEPT ![a] = Loc0]
  /\ UNCHANGED <<files, quarantine, journal, forkIdx, branch, reuse,
                 clobber, dirty, crashes, nextIno, rnBad, draftsUsed>>

\* update: file and index read-modify-write under the lock. Abstractly it only
\* changes the index when it has to heal a conflicted one.
Update(a) ==
  /\ "Update" \in Ops /\ pc[a] = "idle" /\ lock = None /\ ~index.ok
  /\ index' = RebuiltIdx /\ quarantine' = RebuiltQ /\ dirty' = FALSE
  /\ UNCHANGED <<files, journal, forkIdx, branch, lock, pc, loc, allocated, reuse,
                 clobber, crashes, nextIno, rnBad, draftsUsed>>

\* rebuild-index under the lock (quarantine is append-only and written first, so a
\* crash between the two writes is subsumed by a re-run; atomic here).
Rebuild(a) ==
  /\ "Rebuild" \in Ops /\ pc[a] = "idle" /\ lock = None
  /\ index' = RebuiltIdx /\ quarantine' = RebuiltQ /\ dirty' = FALSE
  /\ UNCHANGED <<files, journal, forkIdx, branch, lock, pc, loc, allocated, reuse,
                 clobber, crashes, nextIno, rnBad, draftsUsed>>

---------------------------------------------------------------------------------
\* renumber-drafts (commands/renumber_drafts.py): refuse on a feature branch; under
\* the lock resume from the journal, or plan from stems + index + quarantine and
\* refuse on any target collision; journal; rewrite; link-then-unlink; rebuild;
\* delete the journal.
RnStart(a) ==
  /\ "Renumber" \in Ops /\ pc[a] = "idle" /\ lock = None /\ branch # "feature"
  /\ IF DOMAIN journal # {}
     THEN /\ lock' = a
          /\ pc' = [pc EXCEPT ![a] = "rn_rw"]
          /\ loc' = [loc EXCEPT ![a].map = journal]
          /\ UNCHANGED <<index, quarantine, dirty, allocated, reuse>>
     ELSE LET I == HIdx
              DI == FmIds \cap Drafts
              floor == Max(NumsIn(DOMAIN files) \cup NumsIn(I.keys) \cup NumsIn(HQ) \cup {I.next - 1}
                           \cup Promised)
              map == [d \in DI |-> floor + Cardinality({e \in DI : e <= d})]
              targets == {map[d] : d \in DI}
          IN /\ DI # {}
             /\ floor + Cardinality(DI) <= MaxNum
             /\ targets \cap (DOMAIN files \cup FmIds) = {}   \* else refuse: no change
             /\ lock' = a
             /\ pc' = [pc EXCEPT ![a] = "rn_journal"]
             /\ loc' = [loc EXCEPT ![a].map = map]
             /\ reuse' = (reuse \/ targets \cap allocated # {})
             /\ index' = I /\ quarantine' = HQ /\ dirty' = HDirty
             /\ UNCHANGED allocated
  /\ UNCHANGED <<files, journal, forkIdx, branch, clobber, crashes, nextIno, rnBad, draftsUsed>>

\* The journal is the durable promise: its targets count as allocated from here.
RnJournal(a) ==
  /\ pc[a] = "rn_journal"
  /\ journal' = loc[a].map
  /\ allocated' = allocated \cup {loc[a].map[d] : d \in DOMAIN loc[a].map}
  /\ pc' = [pc EXCEPT ![a] = "rn_rw"]
  /\ UNCHANGED <<files, index, quarantine, forkIdx, branch, lock, loc,
                 reuse, clobber, dirty, crashes, nextIno, rnBad, draftsUsed>>

\* draft_ids.rewrite_references: one atomic_write per file that mentions a
\* draft id (frontmatter id here), and one for the index keys.
RnRewrite(a) ==
  /\ pc[a] = "rn_rw"
  /\ LET M == loc[a].map
         W == {n \in DOMAIN files : files[n].id \in DOMAIN M}
         IK == index.keys \cap DOMAIN M
     IN IF W = {} /\ IK = {}
        THEN /\ pc' = [pc EXCEPT ![a] = "rn_mv"]
             /\ UNCHANGED <<files, index>>
        ELSE /\ \/ \E n \in W : files' = [files EXCEPT ![n].id = M[files[n].id]]
                                /\ UNCHANGED index
                \/ /\ W = {} /\ IK # {}     \* code order: *.md first, then _index.yaml
                   /\ index' = [index EXCEPT !.keys = (@ \ DOMAIN M) \cup {M[k] : k \in IK}]
                   /\ UNCHANGED files
             /\ UNCHANGED pc
  /\ UNCHANGED <<quarantine, journal, forkIdx, branch, lock, loc, allocated, reuse,
                 clobber, dirty, crashes, nextIno, rnBad, draftsUsed>>

\* _rename_files, sorted: link then unlink; an existing target that is the same
\* inode is the resumed tail of a link; any other existing target stops the run
\* with the journal kept.
RnMove(a) ==
  /\ pc[a] = "rn_mv"
  /\ LET M == loc[a].map
         S == DOMAIN files \cap DOMAIN M
     IN IF S = {}
        THEN /\ pc' = [pc EXCEPT ![a] = "rn_rebuild"]
             /\ UNCHANGED <<files, lock, loc, rnBad>>
        ELSE LET n == Min(S)
                 t == M[n]
             IN IF t \in DOMAIN files
                THEN IF files[t].ino = files[n].ino
                     THEN /\ files' = Drop(files, n)
                          /\ UNCHANGED <<pc, lock, loc, rnBad>>
                     ELSE /\ rnBad' = TRUE          \* _Collision: stuck
                          /\ lock' = None
                          /\ pc' = [pc EXCEPT ![a] = "idle"]
                          /\ loc' = [loc EXCEPT ![a] = Loc0]
                          /\ UNCHANGED files
                ELSE /\ files' = Put(files, t, files[n])
                     /\ pc' = [pc EXCEPT ![a] = "rn_unlink"]
                     /\ loc' = [loc EXCEPT ![a].src = n]
                     /\ UNCHANGED <<lock, rnBad>>
  /\ UNCHANGED <<index, quarantine, journal, forkIdx, branch, allocated, reuse,
                 clobber, dirty, crashes, nextIno, draftsUsed>>

RnUnlink(a) ==
  /\ pc[a] = "rn_unlink"
  /\ files' = Drop(files, loc[a].src)
  /\ pc' = [pc EXCEPT ![a] = "rn_mv"]
  /\ UNCHANGED <<index, quarantine, journal, forkIdx, branch, lock, loc, allocated,
                 reuse, clobber, dirty, crashes, nextIno, rnBad, draftsUsed>>

RnRebuild(a) ==
  /\ pc[a] = "rn_rebuild"
  /\ index' = RebuiltIdx /\ quarantine' = RebuiltQ /\ dirty' = FALSE
  /\ pc' = [pc EXCEPT ![a] = "rn_done"]
  /\ UNCHANGED <<files, journal, forkIdx, branch, lock, loc, allocated, reuse,
                 clobber, crashes, nextIno, rnBad, draftsUsed>>

\* I5 is checked when a run ends: every name carries its own id and no journalled
\* draft survives, i.e. the state an uncrashed run reaches.
Converged(M) == \A n \in DOMAIN files : files[n].id = n /\ n \notin DOMAIN M

RnDone(a) ==
  /\ pc[a] = "rn_done"
  /\ journal' = NoMap
  /\ rnBad' = (rnBad \/ ~Converged(loc[a].map))
  /\ lock' = None /\ pc' = [pc EXCEPT ![a] = "idle"] /\ loc' = [loc EXCEPT ![a] = Loc0]
  /\ UNCHANGED <<files, index, quarantine, forkIdx, branch, allocated, reuse,
                 clobber, dirty, crashes, nextIno, draftsUsed>>

---------------------------------------------------------------------------------
\* Crash between any two writes: the process dies, the kernel drops its flock.
Crash(a) ==
  /\ "Crash" \in Ops /\ pc[a] # "idle" /\ crashes < MaxCrashes
  /\ crashes' = crashes + 1 /\ dirty' = TRUE
  /\ lock' = IF lock = a THEN None ELSE lock
  /\ pc' = [pc EXCEPT ![a] = "idle"] /\ loc' = [loc EXCEPT ![a] = Loc0]
  /\ UNCHANGED <<files, index, quarantine, journal, forkIdx, branch, allocated, reuse,
                 clobber, nextIno, rnBad, draftsUsed>>

\* Environment: a file removed by hand or by git (no lock taken).
Delete ==
  /\ "Delete" \in Ops /\ AllIdle     \* hand edits happen between commands
  /\ \E n \in DOMAIN files : files' = Drop(files, n)
  /\ dirty' = TRUE
  /\ UNCHANGED <<index, quarantine, journal, forkIdx, branch, lock, pc, loc, allocated,
                 reuse, clobber, crashes, nextIno, rnBad, draftsUsed>>

\* Environment: another branch forks from the current (committed) index.
Fork ==
  /\ "GitMerge" \in Ops /\ AllIdle /\ index.ok /\ forkIdx # index
  /\ forkIdx' = index
  /\ UNCHANGED <<files, index, quarantine, journal, branch, lock, pc, loc, allocated,
                 reuse, clobber, dirty, crashes, nextIno, rnBad, draftsUsed>>

\* Environment: merge that branch, which created one draft. Artifact files are
\* unioned; the index ends conflicted (salvage = both sides), ours, theirs or union.
GitMerge ==
  /\ "GitMerge" \in Ops /\ AllIdle /\ index.ok /\ nextIno <= MaxIno
  /\ \E d \in Drafts \ draftsUsed, k \in MergeKinds :
       LET theirs == [ok |-> TRUE, keys |-> forkIdx.keys \cup {d}, next |-> forkIdx.next]
           union  == [ok |-> TRUE, keys |-> index.keys \cup theirs.keys,
                      next |-> Max({index.next, theirs.next})]
       IN /\ index' = CASE k = "Ours"     -> index
                        [] k = "Theirs"   -> theirs
                        [] k = "Union"    -> union
                        [] k = "Conflict" -> [union EXCEPT !.ok = FALSE]
          /\ files' = Put(files, d, [id |-> d, ino |-> nextIno])
          /\ nextIno' = nextIno + 1
          /\ draftsUsed' = draftsUsed \cup {d}
          /\ dirty' = TRUE
  /\ UNCHANGED <<quarantine, journal, forkIdx, branch, lock, pc, loc, allocated,
                 reuse, clobber, crashes, rnBad>>

\* Environment: checkout of main, a feature branch, or a detached HEAD.
BranchKind ==
  /\ "Branch" \in Ops /\ AllIdle
  /\ \E b \in Branches : b # branch /\ branch' = b
  /\ UNCHANGED <<files, index, quarantine, journal, forkIdx, lock, pc, loc, allocated,
                 reuse, clobber, dirty, crashes, nextIno, rnBad, draftsUsed>>

Next ==
  \/ \E a \in Actors : \/ CreateAlloc(a) \/ CreateIdx(a) \/ Update(a) \/ Rebuild(a)
                       \/ RnStart(a) \/ RnJournal(a) \/ RnRewrite(a) \/ RnMove(a)
                       \/ RnUnlink(a) \/ RnRebuild(a) \/ RnDone(a) \/ Crash(a)
  \/ Delete \/ Fork \/ GitMerge \/ BranchKind

Spec == Init /\ [][Next]_vars

---------------------------------------------------------------------------------
\* DDD-034 invariants.
I1_NoDupId == \A m, n \in DOMAIN files :
                 (m # n /\ files[m].id = files[n].id) => files[m].ino = files[n].ino
I2_NoOverwrite == ~clobber
I3_NoReuse == ~reuse
I4_IndexIsCache == (AllIdle /\ ~dirty /\ index.ok) =>
                     /\ index.keys = FmIds
                     /\ (allocated = {} \/ index.next > Max(allocated))
I5_RerunConverges == ~rnBad
LockedPcs == {"c_idx", "rn_journal", "rn_rw", "rn_mv", "rn_unlink", "rn_rebuild", "rn_done"}
I6_MutualExclusion == Cardinality({a \in Actors : pc[a] \in LockedPcs}) <= 1

Perms == Permutations(Actors)

TypeOK == /\ lock \in Actors \cup {None}
          /\ crashes \in 0..MaxCrashes
          /\ index.next \in 1..(MaxNum + 1)
=================================================================================
