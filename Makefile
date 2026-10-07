
NAME = fly_in

CC = Python3

SRCS_DIR = srcs

SRCS = $(SRCS_DIR)/main.py \
	   $(SRCS_DIR)/structure.py \


all: $(NAME)

$(NAME):
	$(CC) $(SRCS)

clean:

fclean: clean

re: fclean all
