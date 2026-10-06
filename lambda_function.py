import boto3
from botocore.exceptions import ClientError


# AWS Region
REGION = "ap-south-1"


def lambda_handler(event, context):

    # Create EC2 client
    ec2 = boto3.client(
        "ec2",
        region_name=REGION
    )

    print("====================================")
    print("EBS Snapshot Cleanup Started")
    print("Region:", REGION)
    print("====================================")

    # --------------------------------------------------
    # 1. Get all RUNNING EC2 instances
    # --------------------------------------------------

    try:

        instances_response = ec2.describe_instances(
            Filters=[
                {
                    "Name": "instance-state-name",
                    "Values": ["running"]
                }
            ]
        )

    except ClientError as e:

        print("ERROR: Unable to get EC2 instances")
        print(e)

        return {
            "statusCode": 500,
            "body": "Unable to get EC2 instances"
        }


    # Store running EC2 instance IDs
    running_instance_ids = set()


    for reservation in instances_response.get("Reservations", []):

        for instance in reservation.get("Instances", []):

            instance_id = instance.get("InstanceId")

            if instance_id:

                running_instance_ids.add(instance_id)


    print("Running EC2 instances found:",
          len(running_instance_ids))


    # --------------------------------------------------
    # 2. Get all EBS snapshots owned by this account
    # --------------------------------------------------

    try:

        snapshots_response = ec2.describe_snapshots(
            OwnerIds=["self"]
        )

    except ClientError as e:

        print("ERROR: Unable to get snapshots")
        print(e)

        return {
            "statusCode": 500,
            "body": "Unable to get snapshots"
        }


    snapshots = snapshots_response.get(
        "Snapshots",
        []
    )


    print("Snapshots found:", len(snapshots))


    # Counters
    deleted_count = 0
    kept_count = 0
    skipped_count = 0


    # --------------------------------------------------
    # 3. Check every snapshot
    # --------------------------------------------------

    for snapshot in snapshots:

        snapshot_id = snapshot.get(
            "SnapshotId"
        )

        volume_id = snapshot.get(
            "VolumeId"
        )


        print("------------------------------------")
        print("Checking snapshot:", snapshot_id)


        # --------------------------------------------------
        # 4. If snapshot has no VolumeId
        # --------------------------------------------------

        if not volume_id:

            print(
                "No source volume found."
            )

            try:

                ec2.delete_snapshot(
                    SnapshotId=snapshot_id
                )

                print(
                    "Deleted snapshot:",
                    snapshot_id
                )

                deleted_count += 1

            except ClientError as e:

                error_code = e.response[
                    "Error"
                ]["Code"]


                if error_code == "InvalidSnapshot.NotFound":

                    print(
                        "Snapshot already deleted. Skipping."
                    )

                    skipped_count += 1

                else:

                    print(
                        "Delete failed:",
                        error_code
                    )

            continue


        # --------------------------------------------------
        # 5. Find the EBS volume
        # --------------------------------------------------

        try:

            volume_response = ec2.describe_volumes(
                VolumeIds=[volume_id]
            )


            volumes = volume_response.get(
                "Volumes",
                []
            )


            # Volume doesn't exist
            if not volumes:

                print(
                    "Volume not found:",
                    volume_id
                )

                continue


            volume = volumes[0]


        except ClientError as e:

            error_code = e.response[
                "Error"
            ]["Code"]


            if error_code == "InvalidVolume.NotFound":

                print(
                    "Source volume no longer exists."
                )


                # Try deleting orphan snapshot
                try:

                    ec2.delete_snapshot(
                        SnapshotId=snapshot_id
                    )

                    print(
                        "Deleted orphan snapshot:",
                        snapshot_id
                    )

                    deleted_count += 1


                except ClientError as delete_error:

                    delete_code = delete_error.response[
                        "Error"
                    ]["Code"]


                    if delete_code == "InvalidSnapshot.NotFound":

                        print(
                            "Snapshot already deleted."
                        )

                        skipped_count += 1

                    else:

                        print(
                            "Unable to delete snapshot:",
                            delete_code
                        )


                continue


            else:

                print(
                    "Unable to check volume:",
                    error_code
                )

                continue


        # --------------------------------------------------
        # 6. Check volume attachments
        # --------------------------------------------------

        attachments = volume.get(
            "Attachments",
            []
        )


        attached_to_running_instance = False


        for attachment in attachments:

            instance_id = attachment.get(
                "InstanceId"
            )


            if instance_id in running_instance_ids:

                attached_to_running_instance = True

                break


        # --------------------------------------------------
        # 7. Keep snapshot if volume is used by
        #    a RUNNING instance
        # --------------------------------------------------

        if attached_to_running_instance:

            print(
                "KEEP snapshot:",
                snapshot_id
            )

            print(
                "Reason: Source volume is attached "
                "to a running EC2 instance."
            )

            kept_count += 1

            continue


        # --------------------------------------------------
        # 8. Delete snapshot if source volume is not
        #    attached to a running instance
        # --------------------------------------------------

        print(
            "Snapshot is eligible for deletion:",
            snapshot_id
        )


        try:

            ec2.delete_snapshot(
                SnapshotId=snapshot_id
            )


            print(
                "SUCCESS: Deleted snapshot:",
                snapshot_id
            )


            deleted_count += 1


        except ClientError as e:

            error_code = e.response[
                "Error"
            ]["Code"]


            if error_code == "InvalidSnapshot.NotFound":

                print(
                    "Snapshot no longer exists. Skipping."
                )

                skipped_count += 1


            else:

                print(
                    "Delete failed:",
                    error_code
                )


    # --------------------------------------------------
    # 9. Final summary
    # --------------------------------------------------

    print("====================================")
    print("EBS Snapshot Cleanup Completed")
    print("====================================")

    print(
        "Running instances:",
        len(running_instance_ids)
    )

    print(
        "Total snapshots:",
        len(snapshots)
    )

    print(
        "Snapshots kept:",
        kept_count
    )

    print(
        "Snapshots deleted:",
        deleted_count
    )

    print(
        "Snapshots skipped:",
        skipped_count
    )

    print("====================================")


    # --------------------------------------------------
    # 10. Lambda response
    # --------------------------------------------------

    return {

        "statusCode": 200,

        "body": {

            "message":
                "EBS snapshot cleanup completed",

            "region":
                REGION,

            "running_instances":
                len(running_instance_ids),

            "total_snapshots":
                len(snapshots),

            "snapshots_kept":
                kept_count,

            "snapshots_deleted":
                deleted_count,

            "snapshots_skipped":
                skipped_count
        }
    }