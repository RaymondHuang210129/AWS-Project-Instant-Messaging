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

class queue2
{
private:
	vector<int> dhqueue;
public:
	int size()
	{
		return dhqueue.size();
	}
	int front1()
	{
		return dhqueue[0];
	}
	int front2()
	{
		return dhqueue[1];
	}
	void push(int insert)
	{
		dhqueue.push_back(insert);
	}
	void pop1()
	{
		dhqueue.erase(dhqueue.begin(), dhqueue.begin() + 1);
	}
	void pop2()
	{
		dhqueue.erase(dhqueue.begin() + 1, dhqueue.begin() + 2);
	}
};



int guarantee;
int global_round;
int numcustumer;
struct player { int arrivaltime; int  contplayround; int resttime; int totalround; };
vector<player> players;
queue2 wait_line;
vector<int> playing1, playing2;
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
				pthread_mutex_lock(&mutex);
				if (!playing1.size() && !wait_line.size()) //nobody playing #1 and waiting
				{
					playing1.push_back(id);
					cout << Time << " " << id + 1 << " start playing #1" << endl;
					pthread_mutex_unlock(&mutex);
					state = STATE_PLAY;
				}
				else if (!playing2.size() && !wait_line.size()) //nobody playing #1 and waiting
				{
					playing2.push_back(id);
					cout << Time << " " << id + 1 << " start playing #2" << endl;
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
		case STATE_WAIT:
			sem_wait(&time_sem);
			pthread_mutex_lock(&mutex);
			if (!playing1.size() && (wait_line.front1() == id || wait_line.front2() == id)) //nobody playing 1 and player is the head of queue
			{
				if(wait_line.front1() == id)
				{
					wait_line.pop1();
				}
				else
				{
					wait_line.pop2();
				}
				playing1.push_back(id);
				cout << Time << " " << id + 1 << " start playing #1" << endl;
				pthread_mutex_unlock(&mutex);
				state = STATE_PLAY;
			}
			else if (!playing2.size() && (wait_line.front1() == id || wait_line.front2() == id)) //nobody playing 2 and player is the head of queue
			{
				if(wait_line.front1() == id)
				{
					wait_line.pop1();
				}
				else
				{
					wait_line.pop2();
				}
				playing2.push_back(id);
				cout << Time << " " << id + 1 << " start playing #2" << endl;
				pthread_mutex_unlock(&mutex);
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
				if (!playing1.size() && !wait_line.size()) //nobody playing 1 and waiting
				{
					playing1.push_back(id);
					cout << Time << " " << id + 1 << " start playing #1" << endl;
					pthread_mutex_unlock(&mutex);
					state = STATE_PLAY;
				}
				else if (!playing2.size() && !wait_line.size()) //nobody playing 2 and waiting
				{
					playing2.push_back(id);
					cout << Time << " " << id + 1 << " start playing #2" << endl;
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
			pthread_mutex_lock(&mutex);
			global_round++;
			if (global_round == guarantee)
			{
				global_round = 0;
				if (playing1.front() == id)
				{
					playing1.pop_back();
					cout << Time << " " << id + 1 << " finishing playing YES #1" << endl;
				}
				else
				{
					playing2.pop_back();
					cout << Time << " " << id + 1 << " finishing playing YES #2" << endl;
				}
				pthread_mutex_unlock(&mutex);
				state = STATE_LEAVE;

			}
			else if (total_round == players[id].totalround)
			{
				if (playing1.front() == id)
				{
					playing1.pop_back();
					cout << Time << " " << id + 1 << " finishing playing YES #1" << endl;
				}
				else
				{
					playing2.pop_back();
					cout << Time << " " << id + 1 << " finishing playing YES #2" << endl;
				}
				pthread_mutex_unlock(&mutex);
				state = STATE_LEAVE;

			}
			else if (play_round == players[id].contplayround)
			{
				play_round = 0;
				rest_round = 0;
				if (playing1.front() == id)
				{
					playing1.pop_back();
					cout << Time << " " << id + 1 << " finishing playing NO #1" << endl;
				}
				else
				{
					playing2.pop_back();
					cout << Time << " " << id + 1 << " finishing playing NO #2" << endl;
				}
				pthread_mutex_unlock(&mutex);
				state = STATE_REST;
			}
			else
			{
				pthread_mutex_unlock(&mutex);	
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
		pthread_mutex_lock(&mutex);
		int active = playing1.size() + playing2.size();
		pthread_mutex_unlock(&mutex);

		for (int i = 0; i < active; i++)
		{
			sem_post(&time_prior_sem);
		}
		for (int i = 0; i < active; i++)
		{
			sem_wait(&complete_prior_sem);
		}
		for (int i = active; i < numcustumer; i++)
		{
			sem_post(&time_sem);
		}
		for (int i = active; i < numcustumer; i++)
		{
			sem_wait(&complete_sem);
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
	}
	
	
}

