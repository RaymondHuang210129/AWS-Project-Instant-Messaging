#include <pthread.h>
#include <unistd.h>
#include <time.h>
#include <sys/types.h>
#include <iostream>
#include <fstream>
#include <vector>
#include <queue>
#include <cstdlib>
#include <semaphore.h>

using namespace std;
int guarantee;
int global_round;
int numcustumer;
struct player { int arrivaltime; int  contplayround; int resttime; int totalround; };
vector<player> players;
queue<int> wait_line;
vector<int> playing;
sem_t time_prior_sem;
sem_t time_sem;
sem_t complete_prior_sem;
sem_t complete_sem;
sem_t checkpoint_sem;
sem_t checkpoint2_sem;
pthread_mutex_t mutex;
int Time;

#define STATE_NOT_ARRIVE 0
#define STATE_WAIT 1
#define STATE_REST 2
#define STATE_PLAY 3
#define STATE_LEAVE 4


void *play(int id)
{
	//cout << "thread created" << endl;
	int total_round = 0; 
	int play_round = 0;
	int rest_round = 0;
	int state = STATE_NOT_ARRIVE;
	while (1)
	{
		switch (state)
		{
		case STATE_NOT_ARRIVE:
			sem_wait(&time_sem);
			if (Time >= players[id].arrivaltime)
			{
				//cout << id << "try to get lock" << endl;
				pthread_mutex_lock(&mutex);
				//cout << id << " take lock" << endl;
				if (!playing.size() && !wait_line.size()) //nobody playing
				{
					playing.push_back(id);
					cout << Time << " " << id + 1 << " start playing" << endl;
					pthread_mutex_unlock(&mutex);
					state = STATE_PLAY;
				}
				else
				{
					wait_line.push(id);
					cout << Time << " " << id + 1 << " wait in line" << endl;
					pthread_mutex_unlock(&mutex);
					state = STATE_WAIT;
				}
			}
			else
			{
				//cout << Time << " " << id + 1 << " not arrived" << endl;
			}
			sem_post(&complete_sem);
			break;
		case STATE_WAIT:
			sem_wait(&time_sem);
			//cout << id << "try to get lock" << endl;
			pthread_mutex_lock(&mutex);
			//cout << id << " take lock" << endl;
			if (!playing.size() && wait_line.front() == id) //nobody playing and player is the head of queue
			{
				wait_line.pop();
				playing.push_back(id);
				cout << Time << " " << id + 1 << " start playing" << endl;
				pthread_mutex_unlock(&mutex);
				//cout << "release lock" << endl;
				state = STATE_PLAY;
			}
			else
			{
				pthread_mutex_unlock(&mutex);
			}
			sem_post(&complete_sem);
			break;
		case STATE_REST:
			sem_wait(&time_sem);
			rest_round++;
			if (rest_round == players[id].resttime) // rest enough
			{
				play_round = 0;
				pthread_mutex_lock(&mutex);
				if (!playing.size()) //nobody playing
				{
					playing.push_back(id);
					cout << Time << " " << id + 1 << " start playing" << endl;
					pthread_mutex_unlock(&mutex);
					state = STATE_PLAY;
				}
				else
				{
					wait_line.push(id);
					cout << Time << " " << id + 1 << " wait in line" << endl;
					pthread_mutex_unlock(&mutex);
					state = STATE_WAIT;
				}
			}
			sem_post(&complete_sem);
			break;
		case STATE_PLAY:
			sem_wait(&time_prior_sem);
			play_round++;
			total_round++;
			global_round++;
			if (global_round == guarantee)
			{
				global_round = 0;
				pthread_mutex_lock(&mutex);
				playing.pop_back();
				cout << Time << " " << id + 1 << " finishing playing YES" << endl;
				pthread_mutex_unlock(&mutex);
				state = STATE_LEAVE;

			}
			else if (total_round == players[id].totalround)
			{
				pthread_mutex_lock(&mutex);
				playing.pop_back();
				cout << Time << " " << id + 1 << " finishing playing YES" << endl;
				pthread_mutex_unlock(&mutex);
				state = STATE_LEAVE;

			}
			else if (play_round == players[id].contplayround)
			{
				play_round = 0;
				rest_round = 0;
				pthread_mutex_lock(&mutex);
				playing.pop_back();
				cout << Time << " " << id + 1 << " finishing playing NO" << endl;
				pthread_mutex_unlock(&mutex);
				state = STATE_REST;
			}
			sem_post(&complete_prior_sem);
			break;
		case STATE_LEAVE:
			sem_wait(&time_sem);
			sem_post(&complete_sem);
			break;
		default:
			break;
		}
		sem_wait(&checkpoint_sem);
		sem_post(&checkpoint2_sem);
	}


}

int main(int argc, char *argv[])
{
	ifstream input;
	pthread_attr_t attr;
	pthread_t tid;
	pthread_attr_init(&attr);
	sem_init(&time_sem, 0, 0);
	sem_init(&time_prior_sem, 0, 0);
	sem_init(&complete_sem, 0, 0);
	sem_init(&complete_prior_sem, 0, 0);
	sem_init(&checkpoint_sem, 0, 0);
	sem_init(&checkpoint2_sem, 0, 0);
	pthread_mutex_init(&mutex, NULL);
	input.open(argv[1]);
	input >> guarantee >> numcustumer;
	for (int i = 0; i < numcustumer; i++)
	{
		player player;
		input >> player.arrivaltime >> player.contplayround >> player.resttime >> player.totalround;
		players.push_back(player);
	}
	for (int i = 0; i < numcustumer; i++)
	{
		pthread_create(&tid, &attr, (void *(*)(void *))play, (void *)i);
	}
	input.close();
	Time = 0;
	global_round = 0;
	for(int i = 0; i < 2000; i++)
	{
		//cout << "aa" << endl;
		pthread_mutex_lock(&mutex);
		//cout << "ss" << endl;
		if (!playing.size()) //nobody playing
		{
			pthread_mutex_unlock(&mutex);
			for (int i = 0; i < numcustumer; i++)
			{
				sem_post(&time_sem);
			}
			for (int i = 0; i < numcustumer; i++)
			{
				sem_wait(&complete_sem);
			}
		}
		else //somebody playing
		{
			pthread_mutex_unlock(&mutex);
			sem_post(&time_prior_sem);
			sem_wait(&complete_prior_sem);
			for (int i = 1; i < numcustumer; i++)
			{
				sem_post(&time_sem);
			}
			for (int i = 1; i < numcustumer; i++)
			{
				sem_wait(&complete_sem);
			}
		}

		for (int i = 0; i < numcustumer; i++)
		{
			sem_post(&checkpoint_sem);
		}
		for (int i = 0; i < numcustumer; i++)
		{
			sem_wait(&checkpoint2_sem);
		}

		
		Time++;
		//cout << Time << endl;
		//sleep(1);
	}
	
	
}
