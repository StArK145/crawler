data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  # This is Canonical's official AWS Account ID. It works globally.
  owners = ["099720109477"] 
}

resource "aws_key_pair" "deployer" {
  key_name   = "deployer-key"
  public_key = file(var.public_key_path)
}

resource "aws_instance" "web_server" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.micro"

  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.web_sg.id]
  key_name               = aws_key_pair.deployer.key_name

  user_data = <<-EOF
              #!/bin/bash
              sudo fallocate -l 4G /swapfile
              sudo chmod 600 /swapfile
              sudo mkswap /swapfile
              sudo swapon /swapfile
              echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
              sudo apt-get update
              sudo apt-get install -y docker.io docker-compose-v2
              sudo systemctl enable --now docker
              sudo usermod -aG docker ubuntu
              EOF

  tags = {
    Name = "frontend-pipeline-server"
  }
}
