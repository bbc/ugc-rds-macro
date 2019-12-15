key_id="aws kms list-aliases | jq '.Aliases[]  | select(.AliasName==\"alias/$1-ugc-postgres-passwords-key\")| .TargetKeyId'"
eval id=\$\($key_id\)
echo key-id=$id
if [ -z "$id" ]
then
      echo "key-id not found"
else
m="aws kms put-key-policy --policy-name default --key-id $id --policy file:///home/vagrant/workspace/ugc-rds-macro/scripts/key_policy.json"
eval $m
fi
