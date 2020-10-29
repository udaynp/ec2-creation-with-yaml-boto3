# ec2-creation-with-yaml-boto3

run python ec2_user_file.py region subnetid securitygroup


Presently see some issue with root that is the reasom used amazon1 where bydefault we get ext4



How to migrate the root volume from XFS to ext4 on Amazon Linux 2
==================================================================
 1) Create a snapshot of the root volume and create a new volume from the snapshot
 2) Create a New volume with same size of root volume from AWS console 
 3) Launch a temporary instance  (Please note : You need to have all the volume and instance created on same AZ)
 4) Attach the newly created volume to the temporary instance (eg: /dev/xvdf here)
 5) Attach the volume created from the snapshot of the root volume of the original instance to the temporary instance(/dev/xvdg here)
 6) create a partition on newly created volume as mentioned below 
    # fdisk /dev/xvdf
    Command (m for help): n
    Partition type:
    p   primary (0 primary, 0 extended, 4 free)
    e   extended
    Select (default p): p
    Partition number (1-4, default 1): 1
    First sector (2048-10485759, default 2048): 
    Using default value 2048
    Last sector, +sectors or +size{K,M,G} (2048-10485759, default 10485759): 
    Using default value 10485759
    Partition 1 of type Linux and of size 5 GiB is set

    Command (m for help): a
    Selected partition 1

    Command (m for help): w
    The partition table has been altered!

    Calling ioctl() to re-read partition table.
    Syncing disks.

    # mkfs.ext4 -O 64bit /dev/xvdf1   
    # mkdir /sour /dest
    # e2label /dev/xvdf1 /    
    # mount /dev/xvdf1 /dest
    # mount -o nouuid /dev/xvdg1 /sour
    # rsync -aAvX --progress /sour/ /dest/
    # blkid
    /dev/xvda1: LABEL="/" UUID="b24eb1ea-ab1c-47bd-8542-3fd6059814ae" TYPE="xfs" PARTLABEL="Linux" PARTUUID="30d39261-6b0f-4be5-a0f9-1d792f09d753"
    /dev/xvdg1: LABEL="/" UUID="b24eb1ea-ab1c-47bd-8542-3fd6059814ae" TYPE="ext4" PARTUUID="d6f69caa-01"
    /dev/xvdf1: LABEL="/" UUID="88b73e51-3116-43d2-a4f6-eb2b7b90aa87" TYPE="xfs" PARTLABEL="Linux" PARTUUID="30d39261-6b0f-4be5-a0f9-1d792f09d753"

    # vim /dest/etc/fstab        # replace the filesystem type from xfs to ext4. Also change the UUID to match the uuid of the device xvdf1
        UUID="88b73e51-3116-43d2-a4f6-eb2b7b90aa87"    /           ext4    defaults,noatime  1   1
    # vim /dest/etc/default/grub    # update file to include the root device details. i.e in this example root=UUID="88b73e51-3116-43d2-a4f6-eb2b7b90aa87" on the GRUB_CMDLINE_LINUX_DEFAULT parameter

    GRUB_CMDLINE_LINUX_DEFAULT="console=tty0 console=ttyS0,115200n8 net.ifnames=0 biosdevname=0 root=UUID="88b73e51-3116-43d2-a4f6-eb2b7b90aa87" nvme_core.io_timeout=4294967295 rd.emergency=poweroff rd.shell=0"

    # for i in dev proc sys run ; do mount -o bind /$i /dest/$i; done
    # chroot /dest
    # grub2-install /dev/xvdg
    Installing for i386-pc platform.
    Installation finished. No error reported.


Once you have completed the above mentioned steps, you need to verify the /boot/grub2/grub.cfg file (/dest/boot/grub2/grub.cfg) and make sure that the root volume entries are updated with new UUID. Please see the reference mentioned below for the same. eg (	linux16 /boot/vmlinuz-4.14.193-149.317.amzn2.x86_64 root=UUID=88b73e51-3116-43d2-a4f6-eb2b7b90aa87 ro  console=tty0 console=ttyS0,115200n8 net.ifnames=0 biosdevname=0 root=UUID=88b73e51-3116-43d2-a4f6-eb2b7b90aa87 nvme_core.io_timeout=4294967295 rd.emergency=poweroff rd.shell=0)

To update the same with the required UUID, folow the instruction below as well on the chroot environment. 

    # cp -p /boot/grub2/grub.cfg /boot/grub2/grub.cfg_bak 
    # grub2-mkconfig -o /boot/grub2/grub.cfg 
    # exit 
    # shutdown -h now 

After following these steps, you should be able to boot the instance with newly created ext4 volume as root disk. You need to stop the original instance and swap the root volume from the original disk with the newly created ext4 disk. Once the new instance booted successfully, you can create an AMI out of that to launch other consequent launch with this AMI to have ext4 filesystem. Please note all the Amazon Linux 2 AMI available is using xfs filesystem and you need to follow these instruction and create a custom AMI if you have a requirement to use the ext4 filesystem type for root volume. 
