#!/usr/bin/env bash
set -e

BASE="http://localhost:8010"

echo "Health:"
curl -s $BASE/health | jq .

echo "Create revision:"
REV_ID=$(curl -s -X POST $BASE/datasets/revisions -H "Content-Type: application/json" -d '{"name":"kiv_kat_rev"}' | jq -r .id)
echo "REV_ID=$REV_ID"

echo "Upload glossary:"
curl -s -X POST "$BASE/datasets/revisions/$REV_ID/glossary" -F "file=@sample_data/glossary.csv" | jq .

echo "Upload corpus:"
curl -s -X POST "$BASE/datasets/revisions/$REV_ID/corpus" -F "file=@sample_data/corpus.jsonl" | jq .

echo "Finalize revision:"
curl -s -X POST "$BASE/datasets/revisions/$REV_ID/finalize" | jq .

echo "Start training:"
RUN_ID=$(curl -s -X POST $BASE/train/start -H "Content-Type: application/json" -d "{"model_id":"sema-kiv-kat","revision_id":$REV_ID}" | jq -r .id)
echo "RUN_ID=$RUN_ID"

echo "Wait a bit then check status:"
sleep 3
curl -s $BASE/train/runs/$RUN_ID | jq .

echo "Activate produced version (if any):"
VER=$(curl -s $BASE/train/runs/$RUN_ID | jq -r .produced_version)
if [ "$VER" != "null" ]; then
  curl -s -X POST $BASE/models/sema-kiv-kat/activate/$VER | jq .
fi

echo "Translate:"
curl -s -X POST $BASE/infer/translate -H "Content-Type: application/json" -d '{"source_dialect":"KIV","target_dialect":"KAT","text":"jambo rafiki","model_id":"sema-kiv-kat"}' | jq .
